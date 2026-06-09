package com.brightbean.studio.infrastructure.provider.instagram

import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.InboxItemType
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Sentiment
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.APIError
import com.brightbean.studio.infrastructure.provider.exceptions.OAuthError
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.AccountMetrics
import com.brightbean.studio.infrastructure.provider.types.AuthType
import com.brightbean.studio.infrastructure.provider.types.MediaType
import com.brightbean.studio.infrastructure.provider.types.OAuthTokens
import com.brightbean.studio.infrastructure.provider.types.PostType
import com.brightbean.studio.infrastructure.provider.types.PublishContent
import com.brightbean.studio.infrastructure.provider.types.RateLimitConfig
import com.google.gson.JsonObject
import java.net.URLEncoder
import java.time.Instant
import java.time.format.DateTimeFormatter
import kotlin.time.Duration.Companion.seconds
import kotlin.time.toJavaDuration

class InstagramProvider : AbstractSocialProvider(
    platformType = PlatformType.INSTAGRAM,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 2200,
    supportedPostTypes = listOf(PostType.IMAGE, PostType.CAROUSEL, PostType.REEL, PostType.STORY),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4, MediaType.MOV),
    requiredScopes = listOf(
        "instagram_basic",
        "instagram_content_publish",
        "instagram_manage_comments",
        "instagram_manage_insights",
    ),
    rateLimits = RateLimitConfig(callsPerHour = 200, callsPerDay = 5000, publishPerDay = 100),
) {
    companion object {
        private const val BASE_URL = "https://graph.facebook.com/v21.0"
        private const val OAUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
        private const val TOKEN_URL = "$BASE_URL/oauth/access_token"
        private const val CONTAINER_POLL_INTERVAL_MS = 2000L
        private const val CONTAINER_POLL_MAX_ATTEMPTS = 60
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val params = listOf(
            "client_id" to clientId,
            "redirect_uri" to redirectUri,
            "state" to state,
            "scope" to requiredScopes.joinToString(","),
            "response_type" to "code",
        )
        return "$OAUTH_URL?${urlEncodeParams(params)}"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val response = httpPostForm(TOKEN_URL, mapOf(
            "code" to code,
            "redirect_uri" to redirectUri,
            "client_id" to clientId,
            "client_secret" to clientSecret,
        ))
        val obj = response.asJsonObject
        if (!obj.has("access_token")) {
            throw OAuthError("Instagram token exchange failed", "Instagram", obj.toString())
        }
        return OAuthTokens(
            accessToken = obj["access_token"].asString,
            expiresIn = if (obj.has("expires_in")) obj["expires_in"].asLong else null,
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens {
        val params = listOf(
            "grant_type" to "fb_exchange_token",
            "client_id" to clientId,
            "client_secret" to clientSecret,
            "fb_exchange_token" to refreshToken,
        )
        val response = httpGet("$TOKEN_URL?${urlEncodeParams(params)}")
        val obj = response.asJsonObject
        if (!obj.has("access_token")) {
            throw OAuthError("Instagram long-lived token exchange failed", "Instagram", obj.toString())
        }
        return OAuthTokens(
            accessToken = obj["access_token"].asString,
            expiresIn = if (obj.has("expires_in")) obj["expires_in"].asLong else null,
        )
    }

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["access_token"] ?: return fallbackProfile(account)
        val igUserId = resolveIgUserId(accessToken, account)
        val response = httpGet(
            "$BASE_URL/$igUserId?fields=id,username,name,biography,followers_count,profile_picture_url",
            accessToken,
        )
        val data = response.asJsonObject
        return PlatformProfile(
            platformUserId = data["id"].asString,
            platformUsername = data["username"]?.asString ?: "",
            platformDisplayName = data["name"]?.asString ?: "",
            platformAvatarUrl = data["profile_picture_url"]?.asString,
            profileUrl = "https://instagram.com/${data["username"]?.asString ?: ""}",
            metadata = mapOf("followers" to (data["followers_count"]?.asString ?: "0")),
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")
        val igUserId = content.extra["ig_user_id"]?.toString()
            ?: account.metadata["ig_user_id"]
            ?: resolveIgUserId(accessToken, account)

        return when (content.postType) {
            PostType.CAROUSEL -> publishCarousel(accessToken, igUserId, content)
            else -> publishSingle(accessToken, igUserId, content)
        }
    }

    private fun publishSingle(accessToken: String, igUserId: String, content: PublishContent): PublishResult {
        val payload = JsonObject()
        if (content.text.isNotEmpty()) payload.addProperty("caption", content.text)

        when (content.postType) {
            PostType.REEL -> {
                payload.addProperty("media_type", "REELS")
                payload.addProperty("video_url", content.mediaUrls.firstOrNull() ?: "")
            }
            PostType.STORY -> {
                payload.addProperty("media_type", "STORIES")
                val url = content.mediaUrls.firstOrNull() ?: ""
                if (url.lowercase().endsWith(".mp4") || url.lowercase().endsWith(".mov")) {
                    payload.addProperty("video_url", url)
                } else {
                    payload.addProperty("image_url", url)
                }
            }
            else -> {
                payload.addProperty("image_url", content.mediaUrls.firstOrNull() ?: "")
            }
        }

        val containerId = createContainer(accessToken, igUserId, payload)
        waitForContainer(accessToken, containerId)
        return publishContainer(accessToken, igUserId, containerId)
    }

    private fun publishCarousel(accessToken: String, igUserId: String, content: PublishContent): PublishResult {
        val childIds = mutableListOf<String>()
        for (url in content.mediaUrls) {
            val isVideo = url.lowercase().endsWith(".mp4") || url.lowercase().endsWith(".mov")
            val childPayload = JsonObject().apply {
                addProperty("is_carousel_item", true)
                if (isVideo) {
                    addProperty("media_type", "VIDEO")
                    addProperty("video_url", url)
                } else {
                    addProperty("image_url", url)
                }
            }
            val childId = createContainer(accessToken, igUserId, childPayload)
            waitForContainer(accessToken, childId)
            childIds.add(childId)
        }

        val carouselPayload = JsonObject().apply {
            addProperty("media_type", "CAROUSEL")
            addProperty("children", childIds.joinToString(","))
            if (content.text.isNotEmpty()) addProperty("caption", content.text)
        }
        val carouselId = createContainer(accessToken, igUserId, carouselPayload)
        waitForContainer(accessToken, carouselId)
        return publishContainer(accessToken, igUserId, carouselId)
    }

    private fun createContainer(accessToken: String, igUserId: String, payload: JsonObject): String {
        val response = httpPost("$BASE_URL/$igUserId/media", gson.toJson(payload), accessToken)
        val data = response.asJsonObject
        val containerId = data["id"]?.asString
            ?: throw PublishError("Failed to create Instagram media container", "Instagram", data.toString())
        return containerId
    }

    private fun waitForContainer(accessToken: String, containerId: String) {
        repeat(CONTAINER_POLL_MAX_ATTEMPTS) {
            val response = httpGet("$BASE_URL/$containerId?fields=status_code,status", accessToken)
            val data = response.asJsonObject
            val status = data["status_code"]?.asString ?: ""
            when (status) {
                "FINISHED" -> return
                "ERROR" -> throw PublishError(
                    "Instagram container failed: ${data["status"]?.asString ?: "unknown error"}",
                    "Instagram",
                    data.toString(),
                )
            }
            Thread.sleep(CONTAINER_POLL_INTERVAL_MS)
        }
        throw PublishError("Instagram container processing timed out", "Instagram")
    }

    private fun publishContainer(accessToken: String, igUserId: String, containerId: String): PublishResult {
        val payload = JsonObject().apply { addProperty("creation_id", containerId) }
        val response = httpPost("$BASE_URL/$igUserId/media_publish", gson.toJson(payload), accessToken)
        val data = response.asJsonObject
        val mediaId = data["id"]?.asString ?: ""
        return PublishResult(
            success = true,
            platformPostId = mediaId,
            postUrl = "https://www.instagram.com/p/$mediaId/",
            publishedAt = Instant.now(),
        )
    }

    override fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")
        val payload = JsonObject().apply { addProperty("message", comment) }
        val response = httpPost("$BASE_URL/$postId/comments", gson.toJson(payload), accessToken)
        val data = response.asJsonObject
        return PublishResult(
            success = true,
            platformPostId = data["id"].asString,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.metadata["access_token"] ?: return null
        val metrics = "impressions,reach,engagement,saved"
        val response = httpGet("$BASE_URL/$platformPostId/insights?metric=$metrics", accessToken)
        val values = parseInsightsData(response.asJsonObject)
        return PostInsights(
            platformPostId = platformPostId,
            impressions = values["impressions"] ?: 0L,
            reach = values["reach"] ?: 0L,
            engagementRate = ((values["engagement"] ?: 0L).toDouble()
                .coerceAtMost(Double.MAX_VALUE)),
        )
    }

    override fun getAccountMetrics(account: SocialAccount): AccountMetrics {
        val accessToken = account.metadata["access_token"] ?: return AccountMetrics()
        val igUserId = account.metadata["ig_user_id"] ?: "me"
        val metrics = "impressions,reach,follower_count,profile_views"
        val response = httpGet(
            "$BASE_URL/$igUserId/insights?metric=$metrics&period=day",
            accessToken,
        )
        val values = parseInsightsData(response.asJsonObject)
        return AccountMetrics(
            followers = values["follower_count"] ?: 0L,
            extra = mapOf(
                "impressions" to (values["impressions"] ?: 0L).toString(),
                "reach" to (values["reach"] ?: 0L).toString(),
                "profile_views" to (values["profile_views"] ?: 0L).toString(),
            ),
        )
    }

    override fun getInboxItems(account: SocialAccount): List<InboxItem> {
        val accessToken = account.metadata["access_token"] ?: return emptyList()
        val igUserId = account.metadata["ig_user_id"] ?: return emptyList()
        val response = httpGet(
            "$BASE_URL/$igUserId/conversations?fields=id,participants,messages{id,message,from,created_time}",
            accessToken,
        )
        val conversations = response.asJsonObject["data"]?.asJsonArray ?: return emptyList()
        val messages = mutableListOf<InboxItem>()
        for (convo in conversations) {
            val convoObj = convo.asJsonObject
            val convoId = convoObj["id"].asString
            val msgData = convoObj["messages"]?.asJsonObject?.get("data")?.asJsonArray ?: continue
            for (msg in msgData) {
                val msgObj = msg.asJsonObject
                val sender = msgObj["from"]?.asJsonObject
                messages.add(InboxItem(
                    id = java.util.UUID.randomUUID(),
                    workspaceId = account.workspaceId,
                    socialAccountId = account.id,
                    platformType = PlatformType.INSTAGRAM,
                    platformItemId = msgObj["id"].asString,
                    type = InboxItemType.MESSAGE,
                    content = msgObj["message"]?.asString ?: "",
                    authorName = sender?.get("name")?.asString ?: sender?.get("username")?.asString ?: "",
                    authorAvatarUrl = null,
                    mediaUrls = emptyList(),
                    sentiment = null,
                    isRead = false,
                    isArchived = false,
                    platformCreatedAt = parseTimestamp(msgObj["created_time"]?.asString),
                    receivedAt = Instant.now(),
                ))
            }
        }
        return messages
    }

    private fun resolveIgUserId(accessToken: String, account: SocialAccount): String {
        account.metadata["ig_user_id"]?.let { return it }
        val response = httpGet(
            "$BASE_URL/me/accounts?fields=id,instagram_business_account",
            accessToken,
        )
        val pages = response.asJsonObject["data"]?.asJsonArray ?: return "me"
        for (page in pages) {
            val igAccount = page.asJsonObject["instagram_business_account"]?.asJsonObject
            if (igAccount != null) return igAccount["id"].asString
        }
        throw APIError("No Instagram Business Account found linked to any Facebook Page", "Instagram", 404)
    }

    private fun parseInsightsData(data: com.google.gson.JsonObject): Map<String, Long> {
        val values = mutableMapOf<String, Long>()
        val entries = data["data"]?.asJsonArray ?: return values
        for (entry in entries) {
            val obj = entry.asJsonObject
            val name = obj["name"]?.asString ?: continue
            val vals = obj["values"]?.asJsonArray
            val value = vals?.firstOrNull()?.asJsonObject?.get("value")
            if (value != null && value.isJsonPrimitive && value.asJsonPrimitive.isNumber) {
                values[name] = value.asLong
            }
        }
        return values
    }

    private fun parseTimestamp(ts: String?): Instant {
        if (ts == null) return Instant.now()
        return try {
            val cleaned = ts.replace("+0000", "+00:00")
            Instant.from(DateTimeFormatter.ISO_OFFSET_DATE_TIME.parse(cleaned))
        } catch (_: Exception) {
            Instant.now()
        }
    }

    private fun fallbackProfile(account: SocialAccount) = PlatformProfile(
        platformUserId = account.platformUserId,
        platformUsername = account.platformUsername,
        platformDisplayName = account.platformDisplayName,
        platformAvatarUrl = account.platformAvatarUrl,
        profileUrl = account.profileUrl,
    )

    private fun urlEncodeParams(params: List<Pair<String, String>>): String =
        params.joinToString("&") { "${it.first}=${URLEncoder.encode(it.second, "UTF-8")}" }
}
