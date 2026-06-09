package com.brightbean.studio.infrastructure.provider.mastodon

import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.InboxItemType
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.OAuthError
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.*
import com.google.gson.JsonObject
import org.slf4j.LoggerFactory
import java.net.URLEncoder
import java.time.Instant
import java.util.UUID

class MastodonProvider(
    private val instanceUrl: String,
    private val clientId: String,
    private val clientSecret: String,
) : AbstractSocialProvider(
    platformType = PlatformType.MASTODON,
    authType = AuthType.INSTANCE_OAUTH,
    maxCaptionLength = DEFAULT_MAX_CHARS,
    supportedPostTypes = listOf(PostType.TEXT, PostType.IMAGE, PostType.VIDEO, PostType.POLL),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4, MediaType.MOV, MediaType.WEBP),
    requiredScopes = listOf("read", "write", "follow"),
    rateLimits = RateLimitConfig(callsPerHour = 100, callsPerDay = 7200, publishPerDay = 100),
) {

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val params = mapOf(
            "client_id" to this.clientId,
            "redirect_uri" to redirectUri,
            "scope" to requiredScopes.joinToString(" "),
            "response_type" to "code",
            "state" to state,
        )
        val query = params.entries.joinToString("&") {
            "${it.key}=${URLEncoder.encode(it.value, "UTF-8")}"
        }
        return "$instanceUrl/oauth/authorize?$query"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val formData = mapOf(
            "client_id" to this.clientId,
            "client_secret" to clientSecret,
            "code" to code,
            "redirect_uri" to redirectUri,
            "grant_type" to "authorization_code",
            "scope" to requiredScopes.joinToString(" "),
        )
        val data = httpPostForm("$instanceUrl/oauth/token", formData).asJsonObject
        if (data.has("error")) {
            val desc = data.get("error_description")?.asString ?: data.get("error").asString
            throw OAuthError("Token exchange failed: $desc", platformType.name, data.toString())
        }
        return OAuthTokens(
            accessToken = data.get("access_token").asString,
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens =
        OAuthTokens(accessToken = refreshToken)

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.metadata["accessToken"] ?: return false
        return try {
            val formData = mapOf(
                "client_id" to clientId,
                "client_secret" to clientSecret,
                "token" to accessToken,
            )
            httpPostForm("$instanceUrl/oauth/revoke", formData)
            true
        } catch (e: Exception) {
            logger.error("Failed to revoke Mastodon token: {}", e.message)
            false
        }
    }

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["accessToken"] ?: throw PublishError(
            "No access token for Mastodon account", platformType.name,
        )
        val data = httpGet("$instanceUrl/api/v1/accounts/verify_credentials", accessToken).asJsonObject
        val username = data.get("username")?.asString ?: ""
        return PlatformProfile(
            platformUserId = data.get("id").asString,
            platformUsername = data.get("acct")?.asString ?: username,
            platformDisplayName = data.get("display_name")?.asString ?: username,
            platformAvatarUrl = data.get("avatar")?.asString,
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["accessToken"] ?: throw PublishError(
            "No access token for Mastodon account", platformType.name,
        )

        val mediaIds = mutableListOf<String>()
        for (mediaUrl in content.mediaUrls) {
            val mediaId = uploadMedia(accessToken, mediaUrl)
            mediaIds.add(mediaId)
        }

        val formData = mutableMapOf<String, String>()
        if (content.text.isNotBlank()) {
            formData["status"] = content.text
        }

        val visibility = (content.extra["visibility"] as? String) ?: "public"
        formData["visibility"] = visibility

        (content.extra["spoiler_text"] as? String)?.let {
            formData["spoiler_text"] = it
        }

        (content.extra["in_reply_to_id"] as? String)?.let {
            formData["in_reply_to_id"] = it
        }

        mediaIds.forEachIndexed { index, id ->
            formData["media_ids[$index]"] = id
        }

        if (content.postType == PostType.POLL) {
            @Suppress("UNCHECKED_CAST")
            val poll = content.extra["poll"] as? Map<String, Any>
            if (poll != null) {
                val options = poll["options"] as? List<String> ?: emptyList()
                options.forEachIndexed { index, opt ->
                    formData["poll[options][$index]"] = opt
                }
                formData["poll[expires_in]"] = (poll["expires_in"] as? Number)?.toLong()?.toString() ?: "86400"
                (poll["multiple"] as? Boolean)?.let { formData["poll[multiple]"] = it.toString() }
                (poll["hide_totals"] as? Boolean)?.let { formData["poll[hide_totals]"] = it.toString() }
            }
        }

        val data = httpPostForm("$instanceUrl/api/v1/statuses", formData, accessToken).asJsonObject

        return PublishResult(
            success = true,
            platformPostId = data.get("id").asString,
            postUrl = data.get("url")?.asString,
            publishedAt = Instant.now(),
        )
    }

    override fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult {
        val accessToken = account.metadata["accessToken"] ?: throw PublishError(
            "No access token for Mastodon account", platformType.name,
        )
        val formData = mapOf(
            "status" to comment,
            "in_reply_to_id" to postId,
            "visibility" to "public",
        )
        val data = httpPostForm("$instanceUrl/api/v1/statuses", formData, accessToken).asJsonObject
        return PublishResult(
            success = true,
            platformPostId = data.get("id").asString,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights {
        val accessToken = account.metadata["accessToken"] ?: throw PublishError(
            "No access token for Mastodon account", platformType.name,
        )
        val data = httpGet("$instanceUrl/api/v1/statuses/$platformPostId", accessToken).asJsonObject
        val likes = data.get("favourites_count")?.asLong ?: 0L
        val shares = data.get("reblogs_count")?.asLong ?: 0L
        val comments = data.get("replies_count")?.asLong ?: 0L
        return PostInsights(
            platformPostId = platformPostId,
            likes = likes,
            shares = shares,
            comments = comments,
            engagementRate = if (likes + shares + comments > 0) 1.0 else 0.0,
        )
    }

    override fun getInboxItems(account: SocialAccount): List<InboxItem> {
        val accessToken = account.metadata["accessToken"] ?: return emptyList()
        val types = listOf("mention", "favourite", "reblog")
        val typesParam = types.joinToString(",") { URLEncoder.encode(it, "UTF-8") }
        val data = try {
            httpGet("$instanceUrl/api/v1/notifications?types[]=$typesParam", accessToken).asJsonObject
        } catch (_: Exception) {
            return emptyList()
        }

        if (!data.isJsonArray) return emptyList()
        return data.asJsonArray.mapNotNull { element ->
            val notif = element.asJsonObject
            val notifType = notif.get("type")?.asString ?: return@mapNotNull null
            val accountObj = notif.getAsJsonObject("account")
            val statusObj = notif.getAsJsonObject("status")
            val text = statusObj?.get("content")?.asString?.let { stripHtml(it) } ?: ""
            val createdAt = try {
                Instant.parse(notif.get("created_at")?.asString?.replace("Z", "+00:00") ?: "")
            } catch (_: Exception) {
                Instant.now()
            }

            InboxItem(
                id = UUID.randomUUID(),
                workspaceId = account.workspaceId,
                socialAccountId = account.id,
                platformType = PlatformType.MASTODON,
                platformItemId = notif.get("id")?.asString ?: return@mapNotNull null,
                type = mapNotificationType(notifType),
                content = text,
                authorName = accountObj?.get("display_name")?.asString
                    ?: accountObj?.get("acct")?.asString ?: "",
                authorAvatarUrl = accountObj?.get("avatar")?.asString,
                mediaUrls = emptyList(),
                sentiment = null,
                isRead = false,
                isArchived = false,
                platformCreatedAt = createdAt,
                receivedAt = Instant.now(),
            )
        }
    }

    fun getInstanceMaxChars(accessToken: String): Int {
        return try {
            val data = httpGet("$instanceUrl/api/v2/instance", accessToken).asJsonObject
            data.getAsJsonObject("configuration")
                ?.getAsJsonObject("statuses")
                ?.get("max_characters")?.asInt
                ?: DEFAULT_MAX_CHARS
        } catch (_: Exception) {
            DEFAULT_MAX_CHARS
        }
    }

    fun registerApp(instanceUrl: String, redirectUri: String): Map<String, String> {
        val body = JsonObject().apply {
            addProperty("client_name", "Brightbean")
            addProperty("redirect_uris", redirectUri)
            addProperty("scopes", requiredScopes.joinToString(" "))
            addProperty("website", "https://brightbean.xyz")
        }
        val data = httpPost("${instanceUrl.trimEnd('/')}/api/v1/apps", gson.toJson(body)).asJsonObject
        return mapOf(
            "client_id" to data.get("client_id").asString,
            "client_secret" to data.get("client_secret").asString,
            "instance_url" to instanceUrl,
        )
    }

    private fun uploadMedia(accessToken: String, mediaUrl: String): String {
        val mediaResponse = httpClient.send(
            java.net.http.HttpRequest.newBuilder()
                .uri(java.net.URI.create(mediaUrl))
                .timeout(java.time.Duration.ofSeconds(60))
                .GET()
                .build(),
            java.net.http.HttpResponse.BodyHandlers.ofByteArray(),
        )
        val bytes = mediaResponse.body()
        val filename = mediaUrl.substringAfterLast("/").substringBefore("?")
        val boundary = "----FormBoundary${System.currentTimeMillis()}"
        val multipartBody = buildMultipartBody(boundary, filename, bytes)

        val request = java.net.http.HttpRequest.newBuilder()
            .uri(java.net.URI.create("$instanceUrl/api/v2/media"))
            .timeout(java.time.Duration.ofSeconds(120))
            .header("Authorization", "Bearer $accessToken")
            .header("Content-Type", "multipart/form-data; boundary=$boundary")
            .POST(java.net.http.HttpRequest.BodyPublishers.ofByteArray(multipartBody))
            .build()
        val response = httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() !in 200..299) {
            throw PublishError(
                "Media upload failed (${response.statusCode()}): ${response.body()}",
                platformType.name,
                response.body(),
            )
        }
        val data = gson.fromJson(response.body(), JsonObject::class.java)
        return data.get("id").asString
    }

    private fun buildMultipartBody(boundary: String, filename: String, bytes: ByteArray): ByteArray {
        val sb = StringBuilder()
        sb.append("--$boundary\r\n")
        sb.append("Content-Disposition: form-data; name=\"file\"; filename=\"$filename\"\r\n")
        sb.append("Content-Type: application/octet-stream\r\n\r\n")
        val headerBytes = sb.toString().toByteArray(Charsets.UTF_8)
        val footerBytes = "\r\n--$boundary--\r\n".toByteArray(Charsets.UTF_8)
        return headerBytes + bytes + footerBytes
    }

    private fun stripHtml(html: String): String =
        html.replace(Regex("<[^>]+>"), "")

    private fun mapNotificationType(type: String): InboxItemType = when (type) {
        "mention" -> InboxItemType.MENTION
        "favourite" -> InboxItemType.MESSAGE
        "reblog" -> InboxItemType.SHARE
        else -> InboxItemType.MESSAGE
    }

    companion object {
        private val logger = LoggerFactory.getLogger(MastodonProvider::class.java)
        const val DEFAULT_MAX_CHARS = 500
    }
}
