package com.brightbean.studio.infrastructure.provider.threads

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

class ThreadsProvider : AbstractSocialProvider(
    platformType = PlatformType.THREADS,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 500,
    supportedPostTypes = listOf(PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.CAROUSEL),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.MP4, MediaType.MOV),
    requiredScopes = listOf(
        "threads_basic",
        "threads_content_publish",
        "threads_manage_insights",
        "threads_manage_replies",
    ),
    rateLimits = RateLimitConfig(callsPerHour = 200, callsPerDay = 5000, publishPerDay = 250),
) {
    companion object {
        private const val AUTH_URL = "https://www.threads.com/oauth/authorize"
        private const val TOKEN_URL = "https://graph.threads.net/oauth/access_token"
        private const val API_BASE = "https://graph.threads.net/v1.0"
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val scope = requiredScopes.joinToString(",")
        return "$AUTH_URL?client_id=$clientId&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}" +
            "&state=$state&scope=$scope&response_type=code"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "client_id" to clientId,
            "client_secret" to clientSecret,
            "code" to code,
            "grant_type" to "authorization_code",
            "redirect_uri" to redirectUri,
        ))
        val obj = data.asJsonObject
        val shortLivedToken = obj.get("access_token")?.asString
            ?: throw OAuthError("Threads token exchange failed", platformType.name, data.toString())

        return exchangeForLongLivedToken(shortLivedToken, clientSecret)
    }

    private fun exchangeForLongLivedToken(shortLivedToken: String, clientSecret: String): OAuthTokens {
        val url = "$API_BASE/access_token?grant_type=th_exchange_token&client_secret=$clientSecret&access_token=$shortLivedToken"
        val data = httpGet(url)
        val obj = data.asJsonObject
        if (!obj.has("access_token")) {
            throw OAuthError("Threads long-lived token exchange failed", platformType.name, data.toString())
        }
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens {
        val url = "$API_BASE/refresh_access_token?grant_type=th_refresh_token&access_token=$refreshToken"
        val data = httpGet(url)
        val obj = data.asJsonObject
        if (!obj.has("access_token")) {
            throw OAuthError("Threads token refresh failed", platformType.name, data.toString())
        }
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
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

        val url = "$API_BASE/me?fields=id,username,name,threads_profile_picture_url,threads_biography"
        val data = httpGet(url, accessToken)
        val obj = data.asJsonObject

        return PlatformProfile(
            platformUserId = obj.get("id")?.asString ?: account.platformUserId,
            platformUsername = obj.get("username")?.asString ?: account.platformUsername,
            platformDisplayName = obj.get("name")?.asString ?: account.platformDisplayName,
            platformAvatarUrl = obj.get("threads_profile_picture_url")?.asString ?: account.platformAvatarUrl,
            profileUrl = account.profileUrl,
            metadata = mapOf(
                "biography" to (obj.get("threads_biography")?.asString ?: ""),
            ),
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        val userId = resolveUserId(account, content, accessToken)

        return if (content.postType == PostType.CAROUSEL) {
            publishCarousel(accessToken, userId, content)
        } else {
            publishSingle(accessToken, userId, content)
        }
    }

    @Suppress("UNCHECKED_CAST")
    private fun resolveUserId(account: SocialAccount, content: PublishContent, accessToken: String): String {
        val extraUserId = (content.extra["user_id"] as? String)
        if (!extraUserId.isNullOrBlank()) return extraUserId

        val profile = getProfile(account)
        if (profile.platformUserId.isNotBlank()) return profile.platformUserId

        throw PublishError("Could not determine Threads user_id", platformType.name)
    }

    private fun publishSingle(accessToken: String, userId: String, content: PublishContent): PublishResult {
        val payload = mutableMapOf<String, String>(
            "text" to (content.text.take(maxCaptionLength)),
        )

        when {
            content.postType == PostType.IMAGE && content.mediaUrls.isNotEmpty() -> {
                payload["media_type"] = "IMAGE"
                payload["image_url"] = content.mediaUrls.first()
            }
            content.postType == PostType.VIDEO && content.mediaUrls.isNotEmpty() -> {
                payload["media_type"] = "VIDEO"
                payload["video_url"] = content.mediaUrls.first()
            }
            else -> {
                payload["media_type"] = "TEXT"
            }
        }

        @Suppress("UNCHECKED_CAST")
        val replyTo = content.extra["reply_to_id"] as? String
        if (!replyTo.isNullOrBlank()) {
            payload["reply_to_id"] = replyTo
        }

        val createUrl = "$API_BASE/$userId/threads"
        val formData = payload.entries.joinToString("&") {
            "${it.key}=${URLEncoder.encode(it.value, "UTF-8")}"
        }
        val createData = httpPost(createUrl, formData, accessToken, "application/x-www-form-urlencoded")
        val creationId = createData.asJsonObject.get("id")?.asString
            ?: throw PublishError("Threads container creation failed", platformType.name, createData.toString())

        val publishData = httpPost(
            "$API_BASE/$userId/threads_publish",
            "creation_id=$creationId",
            accessToken,
            "application/x-www-form-urlencoded",
        )
        val threadId = publishData.asJsonObject.get("id")?.asString ?: ""
        return PublishResult(
            success = true,
            platformPostId = threadId,
            publishedAt = Instant.now(),
        )
    }

    private fun publishCarousel(accessToken: String, userId: String, content: PublishContent): PublishResult {
        val childrenIds = mutableListOf<String>()

        for (url in content.mediaUrls) {
            val lowerUrl = url.lowercase()
            val (mediaType, mediaKey) = when {
                lowerUrl.endsWith(".mp4") || lowerUrl.endsWith(".mov") -> "VIDEO" to "video_url"
                else -> "IMAGE" to "image_url"
            }

            val itemFormData = "media_type=$mediaType&$mediaKey=${URLEncoder.encode(url, "UTF-8")}&is_carousel_item=true"
            val itemData = httpPost("$API_BASE/$userId/threads", itemFormData, accessToken, "application/x-www-form-urlencoded")
            val itemId = itemData.asJsonObject.get("id")?.asString
                ?: throw PublishError("Threads carousel item creation failed", platformType.name, itemData.toString())
            childrenIds.add(itemId)
        }

        val childrenParam = childrenIds.joinToString(",")
        val carouselFormData = "media_type=CAROUSEL&children=$childrenParam&text=${URLEncoder.encode(content.text.take(maxCaptionLength), "UTF-8")}"
        val carouselData = httpPost("$API_BASE/$userId/threads", carouselFormData, accessToken, "application/x-www-form-urlencoded")
        val creationId = carouselData.asJsonObject.get("id")?.asString
            ?: throw PublishError("Threads carousel container creation failed", platformType.name, carouselData.toString())

        val publishFormData = "creation_id=$creationId"
        val publishData = httpPost("$API_BASE/$userId/threads_publish", publishFormData, accessToken, "application/x-www-form-urlencoded")
        val threadId = publishData.asJsonObject.get("id")?.asString ?: ""
        return PublishResult(
            success = true,
            platformPostId = threadId,
            publishedAt = Instant.now(),
        )
    }

    override fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        val meUrl = "$API_BASE/me?fields=id"
        val meData = httpGet(meUrl, accessToken)
        val userId = meData.asJsonObject.get("id")?.asString.orEmpty()

        val replyFormData = "media_type=TEXT&text=${URLEncoder.encode(comment.take(maxCaptionLength), "UTF-8")}&reply_to_id=$postId"
        val createData = httpPost("$API_BASE/$userId/threads", replyFormData, accessToken, "application/x-www-form-urlencoded")
        val creationId = createData.asJsonObject.get("id")?.asString
            ?: throw PublishError("Threads reply container creation failed", platformType.name, createData.toString())

        val publishFormData = "creation_id=$creationId"
        val publishData = httpPost("$API_BASE/$userId/threads_publish", publishFormData, accessToken, "application/x-www-form-urlencoded")
        val replyId = publishData.asJsonObject.get("id")?.asString ?: ""
        return PublishResult(
            success = true,
            platformPostId = replyId,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.metadata["access_token"] ?: return null
        val url = "$API_BASE/$platformPostId/insights?metric=views,likes,replies,reposts,quotes"
        val data = httpGet(url, accessToken)

        val metricsArr = data.asJsonObject.getAsJsonArray("data") ?: return null
        val metrics = mutableMapOf<String, Long>()
        for (item in metricsArr) {
            val obj = item.asJsonObject
            val name = obj.get("name")?.asString ?: continue
            val values = obj.getAsJsonArray("values")
            if (values != null && values.size() > 0) {
                metrics[name] = values[0].asJsonObject.get("value")?.asLong ?: 0
            }
        }

        val likes = metrics["likes"] ?: 0
        val replies = metrics["replies"] ?: 0
        val reposts = metrics["reposts"] ?: 0
        val quotes = metrics["quotes"] ?: 0

        return PostInsights(
            platformPostId = platformPostId,
            impressions = metrics["views"] ?: 0,
            likes = likes,
            comments = replies,
            shares = reposts,
        )
    }
}
