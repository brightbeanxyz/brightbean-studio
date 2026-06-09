package com.brightbean.studio.infrastructure.provider.tiktok

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.OAuthError
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.*
import java.net.URLEncoder
import java.time.Instant

class TikTokProvider : AbstractSocialProvider(
    platformType = PlatformType.TIKTOK,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 2200,
    supportedPostTypes = listOf(PostType.VIDEO),
    supportedMediaTypes = listOf(MediaType.MP4, MediaType.MOV),
    requiredScopes = listOf(
        "user.info.basic",
        "video.publish",
        "video.upload",
        "user.info.profile",
        "user.info.stats",
        "video.list",
    ),
    rateLimits = RateLimitConfig(callsPerHour = 200, callsPerDay = 5000, publishPerDay = 5),
) {
    companion object {
        private const val AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
        private const val TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
        private const val API_BASE = "https://open.tiktokapis.com/v2"
        private const val DEFAULT_PRIVACY_LEVEL = "PUBLIC_TO_EVERYONE"
        private val VALID_PRIVACY_LEVELS = setOf(
            "PUBLIC_TO_EVERYONE",
            "MUTUAL_FOLLOW_FRIENDS",
            "FOLLOWER_OF_CREATOR",
            "SELF_ONLY",
        )
        private const val MAX_SINGLE_CHUNK_SIZE = 64_000_000L
        private val CONTENT_TYPE_BY_EXT = mapOf(
            ".mp4" to "video/mp4",
            ".mov" to "video/quicktime",
        )
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val scope = URLEncoder.encode(requiredScopes.joinToString(","), "UTF-8")
        return "$AUTH_URL?client_key=$clientId&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}" +
            "&state=$state&scope=$scope&response_type=code"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "client_key" to clientId,
            "client_secret" to clientSecret,
            "code" to code,
            "grant_type" to "authorization_code",
            "redirect_uri" to redirectUri,
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("TikTok token exchange failed", platformType.name, data.toString())
        }
        val obj = data.asJsonObject
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = obj.get("refresh_token")?.asString,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "client_key" to clientId,
            "client_secret" to clientSecret,
            "refresh_token" to refreshToken,
            "grant_type" to "refresh_token",
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("TikTok token refresh failed", platformType.name, data.toString())
        }
        val obj = data.asJsonObject
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = obj.get("refresh_token")?.asString,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["access_token"]
            ?: return PlatformProfile(
                platformUserId = account.platformUserId,
                platformUsername = account.platformUsername,
                platformDisplayName = account.platformDisplayName,
                platformAvatarUrl = account.platformAvatarUrl,
                profileUrl = account.profileUrl,
            )

        val url = "$API_BASE/user/info/?fields=open_id,union_id,avatar_url,display_name"
        val data = httpGet(url, accessToken)
        val user = data.asJsonObject.getAsJsonObject("data")?.getAsJsonObject("user")
            ?: return PlatformProfile(
                platformUserId = account.platformUserId,
                platformUsername = account.platformUsername,
                platformDisplayName = account.platformDisplayName,
                profileUrl = account.profileUrl,
            )

        return PlatformProfile(
            platformUserId = user.get("open_id")?.asString ?: account.platformUserId,
            platformUsername = account.platformUsername,
            platformDisplayName = user.get("display_name")?.asString ?: account.platformDisplayName,
            platformAvatarUrl = user.get("avatar_url")?.asString ?: account.platformAvatarUrl,
            profileUrl = account.profileUrl,
            metadata = mapOfNotNull("union_id" to user.get("union_id")?.asString),
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        if (content.postType != PostType.VIDEO) {
            throw PublishError("TikTok only supports VIDEO posts", platformType.name)
        }

        val privacyLevel = (content.extra["privacy_level"] as? String) ?: DEFAULT_PRIVACY_LEVEL
        if (privacyLevel !in VALID_PRIVACY_LEVELS) {
            throw PublishError("Invalid privacy_level '$privacyLevel'", platformType.name)
        }

        val title = (content.title ?: content.text).take(maxCaptionLength)

        if (content.mediaUrls.isNotEmpty()) {
            return publishPullFromUrl(accessToken, title, privacyLevel, content.mediaUrls.first())
        }

        throw PublishError("No video source provided (mediaUrls required)", platformType.name)
    }

    private fun publishPullFromUrl(
        accessToken: String,
        title: String,
        privacyLevel: String,
        videoUrl: String,
    ): PublishResult {
        val payload = gson.toJson(mapOf(
            "post_info" to mapOf(
                "title" to title,
                "privacy_level" to privacyLevel,
            ),
            "source_info" to mapOf(
                "source" to "PULL_FROM_URL",
                "video_url" to videoUrl,
            ),
        ))
        val data = httpPost("$API_BASE/post/publish/video/init/", payload, accessToken)
        val publishId = data.asJsonObject.getAsJsonObject("data")?.get("publish_id")?.asString.orEmpty()
        return PublishResult(
            success = true,
            platformPostId = publishId,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        if (platformPostId.isEmpty()) return null

        val accessToken = account.metadata["access_token"] ?: return null
        val videoId = resolveVideoId(accessToken, platformPostId) ?: return null

        val url = "$API_BASE/video/query/?fields=id,view_count,like_count,comment_count,share_count"
        val payload = gson.toJson(mapOf("filters" to mapOf("video_ids" to listOf(videoId))))
        val data = httpPost(url, payload, accessToken)

        val videos = data.asJsonObject.getAsJsonObject("data")?.getAsJsonArray("videos")
            ?: return null
        if (videos.size() == 0) return null

        val video = videos[0].asJsonObject
        return PostInsights(
            platformPostId = platformPostId,
            likes = video.get("like_count")?.asLong ?: 0,
            comments = video.get("comment_count")?.asLong ?: 0,
            shares = video.get("share_count")?.asLong ?: 0,
        )
    }

    override fun getAccountMetrics(account: SocialAccount): AccountMetrics {
        val accessToken = account.metadata["access_token"] ?: return AccountMetrics()
        val url = "$API_BASE/user/info/?fields=follower_count"
        val data = httpGet(url, accessToken)
        val user = data.asJsonObject.getAsJsonObject("data")?.getAsJsonObject("user")
        val followers = user?.get("follower_count")?.asLong ?: 0
        return AccountMetrics(followers = followers)
    }

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.metadata["access_token"] ?: return false
        val clientKey = account.metadata["client_key"] ?: return false
        return try {
            httpPostForm("$API_BASE/oauth/revoke/", mapOf(
                "client_key" to clientKey,
                "token" to accessToken,
            ))
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun resolveVideoId(accessToken: String, postId: String): String? {
        if (postId.isEmpty()) return null
        if (postId.all { it.isDigit() }) return postId

        val payload = gson.toJson(mapOf("publish_id" to postId))
        val data = httpPost("$API_BASE/post/publish/status/fetch/", payload, accessToken)
        val statusData = data.asJsonObject.getAsJsonObject("data") ?: return null
        if (statusData.get("status")?.asString != "PUBLISH_COMPLETE") return null

        val videoIds = statusData.get("publicaly_available_post_id")
        return when {
            videoIds?.isJsonPrimitive == true -> videoIds.asString.ifEmpty { null }
            videoIds?.isJsonArray == true && videoIds.asJsonArray.size() > 0 ->
                videoIds.asJsonArray[0].asString.ifEmpty { null }
            else -> null
        }
    }

    private fun mapOfNotNull(vararg pairs: Pair<String, String?>): Map<String, String> =
        pairs.filter { it.second != null }.associate { it.first to it.second!! }
}
