package com.brightbean.studio.infrastructure.provider.pinterest

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
import java.util.Base64

class PinterestProvider : AbstractSocialProvider(
    platformType = PlatformType.PINTEREST,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 500,
    supportedPostTypes = listOf(PostType.PIN),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4),
    requiredScopes = listOf("user_accounts:read", "boards:read", "pins:read", "pins:write"),
    rateLimits = RateLimitConfig(callsPerHour = 1000, callsPerDay = 24000, publishPerDay = 25),
) {
    companion object {
        private const val AUTH_URL = "https://www.pinterest.com/oauth/"
        private const val API_BASE = "https://api.pinterest.com/v5"
        private const val TOKEN_URL = "$API_BASE/oauth/token"
    }

    private fun basicAuthHeader(clientId: String, clientSecret: String): Map<String, String> {
        val encoded = Base64.getEncoder().encodeToString("$clientId:$clientSecret".toByteArray())
        return mapOf("Authorization" to "Basic $encoded")
    }

    private fun httpPostWithBasicAuth(
        url: String,
        clientId: String,
        clientSecret: String,
        formData: Map<String, String>,
    ): com.google.gson.JsonElement {
        val headers = basicAuthHeader(clientId, clientSecret)
        val formBody = formData.entries.joinToString("&") {
            "${it.key}=${URLEncoder.encode(it.value, "UTF-8")}"
        }
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(60))
            .header("Content-Type", "application/x-www-form-urlencoded")
        headers.forEach { (k, v) -> requestBuilder.header(k, v) }
        val request = requestBuilder.POST(HttpRequest.BodyPublishers.ofString(formBody)).build()
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())

        if (response.statusCode() == 429) {
            val retryAfter = response.headers().firstValue("Retry-After").orElse(null)?.toIntOrNull()
            throw com.brightbean.studio.infrastructure.provider.exceptions.RateLimitError(
                "Rate limit exceeded", platformType.name, retryAfter, response.body()
            )
        }
        if (response.statusCode() in 400..599) {
            throw com.brightbean.studio.infrastructure.provider.exceptions.APIError(
                "Pinterest API error: ${response.body()}", platformType.name, response.statusCode(), response.body()
            )
        }

        val body = response.body()
        return if (body.isBlank()) com.google.gson.JsonParser.parseString("{}")
        else com.google.gson.JsonParser.parseString(body)
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val scope = URLEncoder.encode(requiredScopes.joinToString(","), "UTF-8")
        return "$AUTH_URL?client_id=$clientId&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}" +
            "&state=$state&scope=$scope&response_type=code"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val data = httpPostWithBasicAuth(TOKEN_URL, clientId, clientSecret, mapOf(
            "code" to code,
            "redirect_uri" to redirectUri,
            "grant_type" to "authorization_code",
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("Pinterest token exchange failed", platformType.name, data.toString())
        }
        val obj = data.asJsonObject
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = obj.get("refresh_token")?.asString,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens {
        val data = httpPostWithBasicAuth(TOKEN_URL, clientId, clientSecret, mapOf(
            "refresh_token" to refreshToken,
            "grant_type" to "refresh_token",
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("Pinterest token refresh failed", platformType.name, data.toString())
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

        val data = httpGet("$API_BASE/user_account", accessToken)
        val obj = data.asJsonObject
        val name = obj.get("business_name")?.asString?.ifEmpty { null }
            ?: obj.get("username")?.asString ?: account.platformDisplayName

        return PlatformProfile(
            platformUserId = obj.get("id")?.asString ?: account.platformUserId,
            platformUsername = obj.get("username")?.asString ?: account.platformUsername,
            platformDisplayName = name,
            platformAvatarUrl = obj.get("profile_image")?.asString ?: account.platformAvatarUrl,
            profileUrl = account.profileUrl,
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        val boardId = content.extra["board_id"] as? String
        if (boardId.isNullOrEmpty()) {
            throw PublishError("board_id is required in content.extra for Pinterest pins", platformType.name)
        }

        val payload = mutableMapOf<String, Any>(
            "board_id" to boardId,
            "description" to (content.description ?: content.text).take(maxCaptionLength),
        )

        content.title?.take(100)?.let { payload["title"] = it }
        content.linkUrl?.let { payload["link"] = it }
        (content.extra["alt_text"] as? String)?.take(500)?.let { payload["alt_text"] = it }

        val isVideo = content.extra["is_video"] as? Boolean ?: false
        if (isVideo) {
            return publishVideoPin(accessToken, content, payload)
        }

        if (content.mediaUrls.isNotEmpty()) {
            payload["media_source"] = mapOf(
                "source_type" to "image_url",
                "url" to content.mediaUrls.first(),
            )
        } else {
            throw PublishError("No media provided for Pinterest pin", platformType.name)
        }

        val body = gson.toJson(payload)
        val data = httpPost("$API_BASE/pins", body, accessToken)
        val pinId = data.asJsonObject.get("id")?.asString.orEmpty()

        return PublishResult(
            success = true,
            platformPostId = pinId,
            postUrl = if (pinId.isNotEmpty()) "https://www.pinterest.com/pin/$pinId/" else null,
            publishedAt = Instant.now(),
        )
    }

    private fun publishVideoPin(
        accessToken: String,
        content: PublishContent,
        payload: MutableMap<String, Any>,
    ): PublishResult {
        val mediaPayload = gson.toJson(mapOf("media_type" to "video"))
        val mediaData = httpPost("$API_BASE/media", mediaPayload, accessToken)
        val mediaObj = mediaData.asJsonObject
        val mediaId = mediaObj.get("media_id")?.asString.orEmpty()
        val uploadUrl = mediaObj.get("upload_url")?.asString

        if (uploadUrl != null && content.mediaUrls.isNotEmpty()) {
            val videoSource = content.mediaUrls.first()
            val videoBytes = readMediaBytes(videoSource)
            httpPut(uploadUrl, videoBytes, contentType = "video/mp4")
        }

        payload["media_source"] = mapOf(
            "source_type" to "video_id",
            "media_id" to mediaId,
        )
        val body = gson.toJson(payload)
        val data = httpPost("$API_BASE/pins", body, accessToken)
        val pinId = data.asJsonObject.get("id")?.asString.orEmpty()

        return PublishResult(
            success = true,
            platformPostId = pinId,
            postUrl = if (pinId.isNotEmpty()) "https://www.pinterest.com/pin/$pinId/" else null,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.metadata["access_token"] ?: return null
        val url = "$API_BASE/pins/$platformPostId/analytics?metric_types=IMPRESSION,PIN_CLICK,SAVE,OUTBOUND_CLICK&start_date=2020-01-01&end_date=2099-12-31"
        val data = httpGet(url, accessToken)
        val allData = data.asJsonObject.getAsJsonObject("all") ?: return null

        return PostInsights(
            platformPostId = platformPostId,
            impressions = allData.get("IMPRESSION")?.asLong ?: 0,
            clicks = allData.get("PIN_CLICK")?.asLong ?: 0,
            shares = allData.get("SAVE")?.asLong ?: 0,
        )
    }

    override fun getAccountMetrics(account: SocialAccount): AccountMetrics {
        val accessToken = account.metadata["access_token"] ?: return AccountMetrics()
        val data = httpGet("$API_BASE/user_account", accessToken)
        val obj = data.asJsonObject
        val followers = obj.get("follower_count")?.asLong ?: 0
        return AccountMetrics(followers = followers)
    }

    override fun revokeToken(account: SocialAccount): Boolean = false

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
