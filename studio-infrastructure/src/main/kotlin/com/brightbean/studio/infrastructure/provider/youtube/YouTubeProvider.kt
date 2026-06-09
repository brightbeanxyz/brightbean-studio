package com.brightbean.studio.infrastructure.provider.youtube

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.OAuthError
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.*
import java.net.URI
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import java.time.Instant

class YouTubeProvider : AbstractSocialProvider(
    platformType = PlatformType.YOUTUBE,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 5000,
    supportedPostTypes = listOf(PostType.VIDEO, PostType.SHORT),
    supportedMediaTypes = listOf(MediaType.MP4, MediaType.MOV),
    requiredScopes = listOf(
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.force-ssl",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ),
    rateLimits = RateLimitConfig(callsPerHour = 600, callsPerDay = 10000, publishPerDay = 6),
) {
    companion object {
        private const val AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
        private const val TOKEN_URL = "https://oauth2.googleapis.com/token"
        private const val REVOKE_URL = "https://oauth2.googleapis.com/revoke"
        private const val API_BASE = "https://www.googleapis.com/youtube/v3"
        private const val UPLOAD_BASE = "https://www.googleapis.com/upload/youtube/v3"
        private const val ANALYTICS_BASE = "https://youtubeanalytics.googleapis.com/v2"
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val scope = URLEncoder.encode(requiredScopes.joinToString(" "), "UTF-8")
        return "$AUTH_URL?client_id=$clientId&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}" +
            "&state=$state&scope=$scope&response_type=code&access_type=offline&prompt=consent"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "code" to code,
            "client_id" to clientId,
            "client_secret" to clientSecret,
            "redirect_uri" to redirectUri,
            "grant_type" to "authorization_code",
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("YouTube token exchange failed", platformType.name, data.toString())
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
            "refresh_token" to refreshToken,
            "client_id" to clientId,
            "client_secret" to clientSecret,
            "grant_type" to "refresh_token",
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("YouTube token refresh failed", platformType.name, data.toString())
        }
        val obj = data.asJsonObject
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = obj.get("refresh_token")?.asString ?: refreshToken,
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

        val url = "$API_BASE/channels?part=snippet,statistics&mine=true"
        val data = httpGet(url, accessToken)
        val items = data.asJsonObject.getAsJsonArray("items")
        if (items == null || items.size() == 0) {
            return PlatformProfile(
                platformUserId = account.platformUserId,
                platformUsername = account.platformUsername,
                platformDisplayName = account.platformDisplayName,
                profileUrl = account.profileUrl,
            )
        }

        val channel = items[0].asJsonObject
        val snippet = channel.getAsJsonObject("snippet")
        val stats = channel.getAsJsonObject("statistics")
        val thumbnails = snippet?.getAsJsonObject("thumbnails")
        val avatarUrl = thumbnails?.getAsJsonObject("default")?.get("url")?.asString
            ?: thumbnails?.getAsJsonObject("medium")?.get("url")?.asString

        return PlatformProfile(
            platformUserId = channel.get("id")?.asString ?: account.platformUserId,
            platformUsername = snippet?.get("customUrl")?.asString ?: account.platformUsername,
            platformDisplayName = snippet?.get("title")?.asString ?: account.platformDisplayName,
            platformAvatarUrl = avatarUrl ?: account.platformAvatarUrl,
            profileUrl = account.profileUrl,
            metadata = mapOf(
                "view_count" to (stats?.get("viewCount")?.asString ?: "0"),
                "video_count" to (stats?.get("videoCount")?.asString ?: "0"),
            ),
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        if (content.postType !in listOf(PostType.VIDEO, PostType.SHORT)) {
            throw PublishError("YouTube only supports VIDEO and SHORT post types", platformType.name)
        }

        var title = (content.title ?: content.text).take(100)
        val description = (content.description ?: content.text).take(maxCaptionLength)

        if (content.postType == PostType.SHORT && !title.contains("#Shorts")) {
            title = "$title #Shorts".trim()
        }

        val privacyStatus = (content.extra["privacy_status"] as? String) ?: "public"
        val madeForKids = content.extra["self_declared_made_for_kids"] as? Boolean ?: false
        val categoryId = (content.extra["category_id"] as? String) ?: "22"

        @Suppress("UNCHECKED_CAST")
        val tags = (content.extra["tags"] as? List<String>) ?: emptyList()

        val metadata = mapOf(
            "snippet" to mapOf(
                "title" to title,
                "description" to description,
                "tags" to tags,
                "categoryId" to categoryId,
            ),
            "status" to mapOf(
                "privacyStatus" to privacyStatus,
                "selfDeclaredMadeForKids" to madeForKids,
            ),
        )

        val initPayload = gson.toJson(metadata)
        val initUrl = "$UPLOAD_BASE/videos?uploadType=resumable&part=snippet,status"
        val initRequest = HttpRequest.newBuilder()
            .uri(URI.create(initUrl))
            .timeout(Duration.ofSeconds(60))
            .header("Authorization", "Bearer $accessToken")
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(initPayload))
            .build()
        val initResponse = httpClient.send(initRequest, HttpResponse.BodyHandlers.ofString())
        if (initResponse.statusCode() >= 400) {
            throw PublishError(
                "YouTube upload init failed: ${initResponse.statusCode()}",
                platformType.name, initResponse.body()
            )
        }

        val uploadUri = initResponse.headers().firstValue("Location").orElse(null)
        if (uploadUri == null) {
            throw PublishError("YouTube did not return a resumable upload URI", platformType.name)
        }

        val videoSource = content.mediaUrls.firstOrNull()
            ?: return PublishResult(success = false, errorMessage = "No video source provided (mediaUrls required)")

        val videoBytes = readMediaBytes(videoSource)

        val uploadRequest = HttpRequest.newBuilder()
            .uri(URI.create(uploadUri))
            .timeout(Duration.ofSeconds(300))
            .header("Content-Type", "video/*")
            .header("Content-Length", videoBytes.size.toString())
            .PUT(HttpRequest.BodyPublishers.ofByteArray(videoBytes))
            .build()
        val uploadResponse = httpClient.send(uploadRequest, HttpResponse.BodyHandlers.ofString())
        if (uploadResponse.statusCode() >= 400) {
            throw PublishError(
                "YouTube video upload failed: ${uploadResponse.statusCode()}",
                platformType.name, uploadResponse.body()
            )
        }

        val uploadBody = com.google.gson.JsonParser.parseString(uploadResponse.body()).asJsonObject
        val videoId = uploadBody.get("id")?.asString.orEmpty()

        return PublishResult(
            success = true,
            platformPostId = videoId,
            postUrl = if (videoId.isNotEmpty()) "https://www.youtube.com/watch?v=$videoId" else null,
            publishedAt = Instant.now(),
        )
    }

    override fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        val payload = gson.toJson(mapOf(
            "snippet" to mapOf(
                "videoId" to postId,
                "topLevelComment" to mapOf(
                    "snippet" to mapOf("textOriginal" to comment)
                ),
            ),
        ))
        val data = httpPost("$API_BASE/commentThreads?part=snippet", payload, accessToken)
        val commentId = data.asJsonObject.get("id")?.asString.orEmpty()
        return PublishResult(
            success = true,
            platformPostId = commentId,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.metadata["access_token"] ?: return null
        val url = "$API_BASE/videos?part=statistics&id=$platformPostId"
        val data = httpGet(url, accessToken)
        val items = data.asJsonObject.getAsJsonArray("items")
        if (items == null || items.size() == 0) return null

        val stats = items[0].asJsonObject.getAsJsonObject("statistics")
        return PostInsights(
            platformPostId = platformPostId,
            likes = stats?.get("likeCount")?.asLong ?: 0,
            comments = stats?.get("commentCount")?.asLong ?: 0,
        )
    }

    override fun getAccountMetrics(account: SocialAccount): AccountMetrics {
        val accessToken = account.metadata["access_token"] ?: return AccountMetrics()
        val url = "$API_BASE/channels?part=statistics&mine=true"
        val data = httpGet(url, accessToken)
        val items = data.asJsonObject.getAsJsonArray("items")
        if (items == null || items.size() == 0) return AccountMetrics()

        val stats = items[0].asJsonObject.getAsJsonObject("statistics")
        val followers = stats?.get("subscriberCount")?.asLong ?: 0
        return AccountMetrics(followers = followers)
    }

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.metadata["access_token"] ?: return false
        return try {
            httpPostForm("$REVOKE_URL?token=$accessToken", emptyMap())
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun readMediaBytes(source: String): ByteArray {
        if (source.startsWith("http://") || source.startsWith("https://")) {
            val client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build()
            val request = HttpRequest.newBuilder()
                .uri(URI.create(source))
                .timeout(Duration.ofSeconds(120))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofByteArray())
            if (response.statusCode() >= 400) {
                throw PublishError("Failed to download media from $source", platformType.name)
            }
            return response.body()
        }
        return java.io.File(source).readBytes()
    }
}
