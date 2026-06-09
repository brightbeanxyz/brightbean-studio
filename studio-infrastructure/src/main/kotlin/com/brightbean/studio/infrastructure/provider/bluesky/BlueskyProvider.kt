package com.brightbean.studio.infrastructure.provider.bluesky

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.*
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import org.slf4j.LoggerFactory
import java.net.URLEncoder
import java.time.Instant
import java.util.regex.Pattern
import kotlin.io.encoding.Base64
import kotlin.io.encoding.ExperimentalEncodingApi

class BlueskyProvider(
    private val pdsUrl: String = DEFAULT_PDS_URL,
) : AbstractSocialProvider(
    platformType = PlatformType.BLUESKY,
    authType = AuthType.SESSION,
    maxCaptionLength = 300,
    supportedPostTypes = listOf(PostType.TEXT, PostType.IMAGE, PostType.VIDEO),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.MP4),
    requiredScopes = emptyList(),
) {

    fun createSession(handle: String, appPassword: String): OAuthTokens {
        val body = JsonObject().apply {
            addProperty("identifier", handle)
            addProperty("password", appPassword)
        }
        val data = httpPost("$pdsUrl/xrpc/com.atproto.server.createSession", gson.toJson(body))
        return OAuthTokens(
            accessToken = data.asJsonObject.get("accessJwt").asString,
            refreshToken = data.asJsonObject.get("refreshJwt").asString,
            expiresIn = accessJwtExpiresIn(data.asJsonObject.get("accessJwt").asString),
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens {
        val request = java.net.http.HttpRequest.newBuilder()
            .uri(java.net.URI.create("$pdsUrl/xrpc/com.atproto.server.refreshSession"))
            .timeout(java.time.Duration.ofSeconds(60))
            .header("Authorization", "Bearer $refreshToken")
            .POST(java.net.http.HttpRequest.BodyPublishers.noBody())
            .build()
        val response = httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() !in 200..299) {
            throw PublishError("Session refresh failed: ${response.body()}", platformType.name, response.body())
        }
        val data = gson.fromJson(response.body(), com.google.gson.JsonObject::class.java)
        return OAuthTokens(
            accessToken = data.get("accessJwt").asString,
            refreshToken = data.get("refreshJwt").asString,
            expiresIn = accessJwtExpiresIn(data.get("accessJwt").asString),
        )
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String =
        throw NotImplementedError("Bluesky uses session-based auth, not OAuth. Use createSession() instead.")

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens =
        throw NotImplementedError("Bluesky uses session-based auth, not OAuth. Use createSession() instead.")

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["accessToken"] ?: throw PublishError(
            "No access token for Bluesky account", platformType.name,
        )
        val session = httpGet("$pdsUrl/xrpc/com.atproto.server.getSession", accessToken).asJsonObject
        val did = session.get("did").asString

        val actorParam = URLEncoder.encode(did, "UTF-8")
        val data = httpGet("$pdsUrl/xrpc/app.bsky.actor.getProfile?actor=$actorParam", accessToken).asJsonObject
        val handle = data.get("handle")?.asString ?: ""

        return PlatformProfile(
            platformUserId = data.get("did")?.asString ?: did,
            platformUsername = handle,
            platformDisplayName = data.get("displayName")?.asString ?: handle,
            platformAvatarUrl = data.get("avatar")?.asString,
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["accessToken"] ?: throw PublishError(
            "No access token for Bluesky account", platformType.name,
        )

        if (content.text.length > maxCaptionLength) {
            throw PublishError(
                "Post text exceeds $maxCaptionLength characters (got ${content.text.length})",
                platformType.name,
            )
        }

        val session = httpGet("$pdsUrl/xrpc/com.atproto.server.getSession", accessToken).asJsonObject
        val did = session.get("did").asString
        val handle = session.get("handle").asString

        val now = Instant.now().toString()
        val record = JsonObject().apply {
            addProperty("\$type", "app.bsky.feed.post")
            addProperty("text", content.text)
            addProperty("createdAt", now)
        }

        val facets = parseFacets(content.text, accessToken)
        if (facets.size() > 0) {
            record.add("facets", facets)
        }

        val embed = buildEmbed(accessToken, content)
        if (embed != null) {
            record.add("embed", embed)
        }

        val requestBody = JsonObject().apply {
            addProperty("repo", did)
            addProperty("collection", "app.bsky.feed.post")
            add("record", record)
        }

        val data = httpPost(
            "$pdsUrl/xrpc/com.atproto.repo.createRecord",
            gson.toJson(requestBody),
            accessToken,
        ).asJsonObject

        val uri = data.get("uri")?.asString ?: ""
        val rkey = uri.substringAfterLast("/")
        val postUrl = if (rkey.isNotBlank()) "https://bsky.app/profile/$handle/post/$rkey" else null

        return PublishResult(
            success = true,
            platformPostId = uri,
            postUrl = postUrl,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.metadata["accessToken"] ?: return null
        val atUri = URLEncoder.encode(platformPostId, "UTF-8")
        val data = try {
            httpGet("$pdsUrl/xrpc/app.bsky.feed.getPostThread?uri=$atUri", accessToken).asJsonObject
        } catch (_: Exception) {
            return null
        }
        val post = data.getAsJsonObject("thread")?.getAsJsonObject("post") ?: return null
        val likeCount = post.getAsJsonObject("likeCount")?.get("\$type")?.asLong
            ?: post.get("likeCount")?.asLong ?: 0L
        val repostCount = post.getAsJsonObject("repostCount")?.get("\$type")?.asLong
            ?: post.get("repostCount")?.asLong ?: 0L
        val replyCount = post.getAsJsonObject("replyCount")?.get("\$type")?.asLong
            ?: post.get("replyCount")?.asLong ?: 0L

        return PostInsights(
            platformPostId = platformPostId,
            likes = likeCount,
            shares = repostCount,
            comments = replyCount,
        )
    }

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.metadata["accessToken"] ?: return false
        return try {
            httpPost("$pdsUrl/xrpc/com.atproto.server.deleteSession", null, accessToken)
            true
        } catch (e: Exception) {
            logger.error("Failed to delete Bluesky session: {}", e.message)
            false
        }
    }

    fun resolveHandle(handle: String): String {
        val encoded = URLEncoder.encode(handle, "UTF-8")
        val data = httpGet("$DEFAULT_PDS_URL/xrpc/com.atproto.identity.resolveHandle?handle=$encoded").asJsonObject
        return data.get("did").asString
    }

    private fun parseFacets(text: String, accessToken: String): JsonArray {
        val facets = JsonArray()
        val utf8Bytes = text.toByteArray(Charsets.UTF_8)

        val linkPattern = Pattern.compile("https?://[^\\s\\)\\]>]+")
        val linkMatcher = linkPattern.matcher(text)
        while (linkMatcher.find()) {
            val byteStart = text.substring(0, linkMatcher.start()).toByteArray(Charsets.UTF_8).size
            val byteEnd = text.substring(0, linkMatcher.end()).toByteArray(Charsets.UTF_8).size
            val feature = JsonObject().apply {
                addProperty("\$type", "app.bsky.richtext.facet#link")
                addProperty("uri", linkMatcher.group())
            }
            val featureArray = JsonArray().apply { add(feature) }
            facets.add(JsonObject().apply {
                add("index", JsonObject().apply {
                    addProperty("byteStart", byteStart)
                    addProperty("byteEnd", byteEnd)
                })
                add("features", featureArray)
            })
        }

        val mentionPattern = Pattern.compile("(?<!\\w)@([\\w.-]+(?:\\.[\\w.-]+)+)")
        val mentionMatcher = mentionPattern.matcher(text)
        while (mentionMatcher.find()) {
            val handle = mentionMatcher.group(1)
            val did = try {
                resolveHandle(handle)
            } catch (e: Exception) {
                logger.warn("Could not resolve handle @{}, skipping facet", handle)
                continue
            }
            val byteStart = text.substring(0, mentionMatcher.start()).toByteArray(Charsets.UTF_8).size
            val byteEnd = text.substring(0, mentionMatcher.end()).toByteArray(Charsets.UTF_8).size
            val feature = JsonObject().apply {
                addProperty("\$type", "app.bsky.richtext.facet#mention")
                addProperty("did", did)
            }
            val featureArray = JsonArray().apply { add(feature) }
            facets.add(JsonObject().apply {
                add("index", JsonObject().apply {
                    addProperty("byteStart", byteStart)
                    addProperty("byteEnd", byteEnd)
                })
                add("features", featureArray)
            })
        }

        val hashtagPattern = Pattern.compile("(?<!\\w)#(\\w+)")
        val hashtagMatcher = hashtagPattern.matcher(text)
        while (hashtagMatcher.find()) {
            val tag = hashtagMatcher.group(1)
            val byteStart = text.substring(0, hashtagMatcher.start()).toByteArray(Charsets.UTF_8).size
            val byteEnd = text.substring(0, hashtagMatcher.end()).toByteArray(Charsets.UTF_8).size
            val feature = JsonObject().apply {
                addProperty("\$type", "app.bsky.richtext.facet#tag")
                addProperty("tag", tag)
            }
            val featureArray = JsonArray().apply { add(feature) }
            facets.add(JsonObject().apply {
                add("index", JsonObject().apply {
                    addProperty("byteStart", byteStart)
                    addProperty("byteEnd", byteEnd)
                })
                add("features", featureArray)
            })
        }

        return facets
    }

    private fun buildEmbed(accessToken: String, content: PublishContent): JsonObject? {
        val mediaUrls = content.mediaUrls
        if (mediaUrls.isEmpty()) return null

        if (content.postType == PostType.VIDEO) {
            val blobRef = uploadBlobFromUrl(accessToken, mediaUrls.first())
            return JsonObject().apply {
                addProperty("\$type", "app.bsky.embed.video")
                add("video", blobRef)
            }
        }

        val images = JsonArray()
        for (url in mediaUrls.take(4)) {
            val blobRef = uploadBlobFromUrl(accessToken, url)
            val imageObj = JsonObject().apply {
                addProperty("alt", (content.extra["alt_text"] as? String) ?: "")
                add("image", blobRef)
            }
            images.add(imageObj)
        }
        return JsonObject().apply {
            addProperty("\$type", "app.bsky.embed.images")
            add("images", images)
        }
    }

    private fun uploadBlobFromUrl(accessToken: String, url: String): JsonObject {
        val mediaResponse = httpClient.send(
            java.net.http.HttpRequest.newBuilder()
                .uri(java.net.URI.create(url))
                .timeout(java.time.Duration.ofSeconds(60))
                .GET()
                .build(),
            java.net.http.HttpResponse.BodyHandlers.ofByteArray(),
        )
        val bytes = mediaResponse.body()
        val contentType = mediaResponse.headers().firstValue("Content-Type").orElse("application/octet-stream")

        val response = httpPut(
            "$pdsUrl/xrpc/com.atproto.repo.uploadBlob",
            bytes,
            accessToken,
            contentType,
        )
        val body = response.body()
        val json = String(body, Charsets.UTF_8)
        val data = gson.fromJson(json, JsonObject::class.java)
        return data.getAsJsonObject("blob")
    }

    @OptIn(ExperimentalEncodingApi::class)
    private fun accessJwtExpiresIn(accessJwt: String): Long? {
        return try {
            val parts = accessJwt.split(".")
            if (parts.size != 3) return null
            val payload = String(Base64.UrlSafe.decode(parts[1]), Charsets.UTF_8)
            val json = gson.fromJson(payload, JsonObject::class.java)
            val exp = json.get("exp")?.asLong ?: return null
            val now = System.currentTimeMillis() / 1000
            maxOf(0L, exp - now)
        } catch (_: Exception) {
            null
        }
    }

    companion object {
        private val logger = LoggerFactory.getLogger(BlueskyProvider::class.java)
        const val DEFAULT_PDS_URL = "https://bsky.social"
    }
}
