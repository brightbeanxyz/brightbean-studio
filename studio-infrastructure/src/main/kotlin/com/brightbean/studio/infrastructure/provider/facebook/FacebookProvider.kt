package com.brightbean.studio.infrastructure.provider.facebook

import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.InboxItemType
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Sentiment
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
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
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

class FacebookProvider : AbstractSocialProvider(
    platformType = PlatformType.FACEBOOK,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 63206,
    supportedPostTypes = listOf(PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.LINK),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4, MediaType.MOV),
    requiredScopes = listOf(
        "business_management", "pages_show_list", "pages_manage_posts",
        "pages_read_engagement", "pages_read_user_content",
        "pages_manage_metadata", "pages_messaging",
    ),
    rateLimits = RateLimitConfig(callsPerHour = 200, callsPerDay = 4800, publishPerDay = 4800),
) {
    companion object {
        private const val BASE_URL = "https://graph.facebook.com/v21.0"
        private const val OAUTH_URL = "https://www.facebook.com/v21.0/dialog/oauth"
        private const val TOKEN_URL = "$BASE_URL/oauth/access_token"
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
            throw OAuthError("Facebook token exchange failed", "Facebook", obj.toString())
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
            throw OAuthError("Facebook long-lived token exchange failed", "Facebook", obj.toString())
        }
        return OAuthTokens(
            accessToken = obj["access_token"].asString,
            expiresIn = if (obj.has("expires_in")) obj["expires_in"].asLong else null,
        )
    }

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["access_token"] ?: return fallbackProfile(account)
        val response = httpGet("$BASE_URL/me?fields=id,name,email,picture.width(200).height(200)", accessToken)
        val data = response.asJsonObject
        val avatarUrl = data["picture"]?.asJsonObject?.get("data")?.asJsonObject?.get("url")?.asString
        return PlatformProfile(
            platformUserId = data["id"].asString,
            platformUsername = "",
            platformDisplayName = data["name"]?.asString ?: "",
            platformAvatarUrl = avatarUrl,
            profileUrl = "https://facebook.com/${data["id"].asString}",
            metadata = mapOf("followers" to "0"),
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["access_token"]
            ?: return PublishResult(success = false, errorMessage = "No access token")
        val pageId = content.extra["page_id"]?.toString()
            ?: return PublishResult(success = false, errorMessage = "page_id is required in content.extra")

        return when (content.postType) {
            PostType.IMAGE -> publishPhoto(accessToken, pageId, content)
            PostType.VIDEO -> publishVideo(accessToken, pageId, content)
            else -> publishTextOrLink(accessToken, pageId, content)
        }
    }

    private fun publishTextOrLink(accessToken: String, pageId: String, content: PublishContent): PublishResult {
        val payload = JsonObject().apply {
            addProperty("message", content.text)
            if (content.linkUrl != null) addProperty("link", content.linkUrl)
        }
        val response = httpPost("$BASE_URL/$pageId/feed", gson.toJson(payload), accessToken)
        val data = response.asJsonObject
        val postId = data["id"].asString
        return PublishResult(
            success = true,
            platformPostId = postId,
            postUrl = "https://www.facebook.com/$postId",
            publishedAt = Instant.now(),
        )
    }

    private fun publishPhoto(accessToken: String, pageId: String, content: PublishContent): PublishResult {
        val payload = JsonObject().apply {
            addProperty("url", content.mediaUrls.firstOrNull() ?: "")
            if (content.text.isNotEmpty()) addProperty("message", content.text)
        }
        val response = httpPost("$BASE_URL/$pageId/photos", gson.toJson(payload), accessToken)
        val data = response.asJsonObject
        val postId = data["id"].asString
        val actualPostId = if (data.has("post_id")) data["post_id"].asString else postId
        return PublishResult(
            success = true,
            platformPostId = postId,
            postUrl = "https://www.facebook.com/$actualPostId",
            publishedAt = Instant.now(),
        )
    }

    private fun publishVideo(accessToken: String, pageId: String, content: PublishContent): PublishResult {
        val payload = JsonObject().apply {
            addProperty("file_url", content.mediaUrls.firstOrNull() ?: "")
            if (content.text.isNotEmpty()) addProperty("description", content.text)
        }
        val response = httpPost("$BASE_URL/$pageId/videos", gson.toJson(payload), accessToken)
        val data = response.asJsonObject
        val postId = data["id"].asString
        return PublishResult(
            success = true,
            platformPostId = postId,
            postUrl = "https://www.facebook.com/$postId",
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
        val metrics = "post_impressions,post_engaged_users,post_clicks,post_reactions_by_type_total"
        val response = httpGet("$BASE_URL/$platformPostId/insights?metric=$metrics", accessToken)
        val values = parseInsightsData(response.asJsonObject)
        val reactions = values["post_reactions_by_type_total"]
        val totalLikes = if (reactions is Map<*, *>) {
            ((reactions["like"] as? Number)?.toLong() ?: 0L) +
                ((reactions["love"] as? Number)?.toLong() ?: 0L)
        } else 0L
        return PostInsights(
            platformPostId = platformPostId,
            impressions = (values["post_impressions"] as? Number)?.toLong() ?: 0L,
            likes = totalLikes,
            clicks = (values["post_clicks"] as? Number)?.toLong() ?: 0L,
        )
    }

    override fun getAccountMetrics(account: SocialAccount): AccountMetrics {
        val accessToken = account.metadata["access_token"] ?: return AccountMetrics()
        val pageId = account.metadata["page_id"] ?: "me"
        val metrics = "page_impressions,page_engaged_users,page_fans"
        val response = httpGet("$BASE_URL/$pageId/insights?metric=$metrics", accessToken)
        val values = parseInsightsData(response.asJsonObject)
        return AccountMetrics(
            followers = (values["page_fans"] as? Number)?.toLong() ?: 0L,
            extra = mapOf(
                "impressions" to ((values["page_impressions"] as? Number)?.toLong() ?: 0L).toString(),
                "engaged_users" to ((values["page_engaged_users"] as? Number)?.toLong() ?: 0L).toString(),
            ),
        )
    }

    override fun getInboxItems(account: SocialAccount): List<InboxItem> {
        val accessToken = account.metadata["access_token"] ?: return emptyList()
        val pageId = account.metadata["page_id"] ?: return emptyList()
        val response = httpGet("$BASE_URL/$pageId/conversations", accessToken)
        val conversations = response.asJsonObject["data"]?.asJsonArray ?: return emptyList()
        val messages = mutableListOf<InboxItem>()
        for (convo in conversations) {
            val convoId = convo.asJsonObject["id"].asString
            val msgResponse = httpGet(
                "$BASE_URL/$convoId/messages?fields=id,message,from,created_time",
                accessToken,
            )
            val msgData = msgResponse.asJsonObject["data"]?.asJsonArray ?: continue
            for (msg in msgData) {
                val msgObj = msg.asJsonObject
                val sender = msgObj["from"]?.asJsonObject
                messages.add(InboxItem(
                    id = java.util.UUID.randomUUID(),
                    workspaceId = account.workspaceId,
                    socialAccountId = account.id,
                    platformType = PlatformType.FACEBOOK,
                    platformItemId = msgObj["id"].asString,
                    type = InboxItemType.MESSAGE,
                    content = msgObj["message"]?.asString ?: "",
                    authorName = sender?.get("name")?.asString ?: "",
                    authorAvatarUrl = null,
                    mediaUrls = emptyList(),
                    sentiment = null,
                    isRead = false,
                    isArchived = false,
                    platformCreatedAt = parseFacebookTimestamp(msgObj["created_time"]?.asString),
                    receivedAt = Instant.now(),
                ))
            }
        }
        return messages
    }

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.metadata["access_token"] ?: return false
        return try {
            httpDelete("$BASE_URL/me/permissions", accessToken)
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun parseInsightsData(data: com.google.gson.JsonObject): Map<String, Any> {
        val values = mutableMapOf<String, Any>()
        val entries = data["data"]?.asJsonArray ?: return values
        for (entry in entries) {
            val obj = entry.asJsonObject
            val name = obj["name"]?.asString ?: continue
            val vals = obj["values"]?.asJsonArray
            val value = vals?.firstOrNull()?.asJsonObject?.get("value")
            if (value != null) {
                if (value.isJsonObject) {
                    val map = mutableMapOf<String, Any>()
                    for ((k, v) in value.asJsonObject.entrySet()) {
                        map[k] = if (v.isJsonPrimitive && v.asJsonPrimitive.isNumber) v.asLong else v.asString
                    }
                    values[name] = map
                } else if (value.isJsonPrimitive && value.asJsonPrimitive.isNumber) {
                    values[name] = value.asLong
                } else {
                    values[name] = value.asString
                }
            }
        }
        return values
    }

    private fun parseFacebookTimestamp(ts: String?): Instant {
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
