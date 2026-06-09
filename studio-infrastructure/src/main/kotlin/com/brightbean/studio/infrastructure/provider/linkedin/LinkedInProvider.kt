package com.brightbean.studio.infrastructure.provider.linkedin

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.APIError
import com.brightbean.studio.infrastructure.provider.exceptions.OAuthError
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.*
import com.google.gson.JsonParser
import java.net.URI
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration
import java.time.Instant
import kotlin.math.min

open class LinkedInProvider(
    platformType: PlatformType = PlatformType.LINKEDIN_COMPANY,
) : AbstractSocialProvider(
    platformType = platformType,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 3000,
    supportedPostTypes = listOf(
        PostType.TEXT, PostType.IMAGE, PostType.VIDEO,
        PostType.LINK, PostType.ARTICLE, PostType.POLL,
    ),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG, MediaType.GIF, MediaType.MP4),
    requiredScopes = listOf(
        "w_member_social", "r_member_social",
        "w_organization_social", "r_organization_social",
    ),
    rateLimits = RateLimitConfig(callsPerHour = 200, callsPerDay = 100, publishPerDay = 100),
) {

    companion object {
        private const val AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
        private const val TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
        private const val REVOKE_URL = "https://www.linkedin.com/oauth/v2/revoke"
        const val API_BASE = "https://api.linkedin.com"

        private val LINKEDIN_HEADERS = mapOf(
            "LinkedIn-Version" to "202604",
            "X-Restli-Protocol-Version" to "2.0.0",
        )
    }

    private fun encodeUrn(urn: String): String =
        URLEncoder.encode(urn, "UTF-8")

    private fun buildLinkedInGet(url: String, accessToken: String): HttpRequest {
        val builder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(30))
            .header("Authorization", "Bearer $accessToken")
        LINKEDIN_HEADERS.forEach { (k, v) -> builder.header(k, v) }
        return builder.GET().build()
    }

    private fun buildLinkedInPost(url: String, accessToken: String, body: String): HttpRequest {
        val builder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(60))
            .header("Authorization", "Bearer $accessToken")
            .header("Content-Type", "application/json")
        LINKEDIN_HEADERS.forEach { (k, v) -> builder.header(k, v) }
        return builder.POST(HttpRequest.BodyPublishers.ofString(body)).build()
    }

    private fun linkedInGet(url: String, accessToken: String) =
        executeLinkedIn(buildLinkedInGet(url, accessToken))

    private fun linkedInPost(url: String, accessToken: String, body: String) =
        executeLinkedIn(buildLinkedInPost(url, accessToken, body))

    private fun executeLinkedIn(request: HttpRequest): com.google.gson.JsonElement {
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
        val statusCode = response.statusCode()
        val responseBody = response.body()

        if (statusCode == 429) {
            val retryAfter = response.headers().firstValue("Retry-After").orElse(null)?.toIntOrNull()
            throw com.brightbean.studio.infrastructure.provider.exceptions.RateLimitError(
                "Rate limit exceeded", platformType.name, retryAfter, responseBody
            )
        }
        if (statusCode in 400..499) {
            throw APIError("LinkedIn API error: $responseBody", platformType.name, statusCode, responseBody)
        }
        if (statusCode in 500..599) {
            throw APIError("LinkedIn server error: $responseBody", platformType.name, statusCode, responseBody)
        }
        return if (responseBody.isBlank()) JsonParser.parseString("{}")
        else JsonParser.parseString(responseBody)
    }

    private fun executeLinkedInForHeaders(request: HttpRequest): HttpResponse<String> {
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
        val statusCode = response.statusCode()
        if (statusCode >= 400) {
            val responseBody = response.body()
            if (statusCode == 429) {
                val retryAfter = response.headers().firstValue("Retry-After").orElse(null)?.toIntOrNull()
                throw com.brightbean.studio.infrastructure.provider.exceptions.RateLimitError(
                    "Rate limit exceeded", platformType.name, retryAfter, responseBody
                )
            }
            throw APIError("LinkedIn API error: $responseBody", platformType.name, statusCode, responseBody)
        }
        return response
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val scope = URLEncoder.encode(requiredScopes.joinToString(" "), "UTF-8")
        return "$AUTH_URL?response_type=code&client_id=$clientId&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}&state=$state&scope=$scope"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "grant_type" to "authorization_code",
            "code" to code,
            "redirect_uri" to redirectUri,
            "client_id" to clientId,
            "client_secret" to clientSecret,
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("LinkedIn token exchange failed", platformType.name, data.toString())
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
            "grant_type" to "refresh_token",
            "refresh_token" to refreshToken,
            "client_id" to clientId,
            "client_secret" to clientSecret,
        ))
        if (!data.asJsonObject.has("access_token")) {
            throw OAuthError("LinkedIn token refresh failed", platformType.name, data.toString())
        }
        val obj = data.asJsonObject
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = obj.get("refresh_token")?.asString,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["accessToken"]
            ?: return PlatformProfile(
                platformUserId = account.platformUserId,
                platformUsername = account.platformUsername,
                platformDisplayName = account.platformDisplayName,
                platformAvatarUrl = account.platformAvatarUrl,
                profileUrl = account.profileUrl,
            )

        val url = "$API_BASE/v2/me?projection=(id,localizedFirstName,localizedLastName,profilePicture(displayImage~:playableStreams))"
        val data = linkedInGet(url, accessToken)
        val obj = data.asJsonObject

        val firstName = obj.get("localizedFirstName")?.asString.orEmpty()
        val lastName = obj.get("localizedLastName")?.asString.orEmpty()
        val name = "$firstName $lastName".trim().ifEmpty { obj.get("vanityName")?.asString.orEmpty() }

        val avatarUrl = runCatching {
            obj.getAsJsonObject("profilePicture")
                .getAsJsonObject("displayImage~")
                .getAsJsonArray("elements")
                .lastOrNull()?.asJsonObject
                ?.getAsJsonArray("identifiers")?.firstOrNull()?.asJsonObject
                ?.get("identifier")?.asString
        }.getOrNull()

        return PlatformProfile(
            platformUserId = obj.get("id")?.asString ?: account.platformUserId,
            platformUsername = obj.get("vanityName")?.asString ?: account.platformUsername,
            platformDisplayName = name,
            platformAvatarUrl = avatarUrl ?: account.platformAvatarUrl,
            profileUrl = account.profileUrl,
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.metadata["accessToken"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        @Suppress("UNCHECKED_CAST")
        val author = (content.extra["author"] as? String)
            ?: run {
                val profile = getProfile(account)
                "urn:li:person:${profile.platformUserId}"
            }

        return when {
            content.postType == PostType.IMAGE && content.mediaUrls.isNotEmpty() ->
                publishImagePost(accessToken, author, content)
            content.postType == PostType.VIDEO && content.mediaUrls.isNotEmpty() ->
                publishVideoPost(accessToken, author, content)
            content.postType == PostType.ARTICLE ->
                publishArticlePost(accessToken, author, content)
            content.postType == PostType.POLL ->
                publishPollPost(accessToken, author, content)
            else -> publishTextPost(accessToken, author, content)
        }
    }

    private fun buildPostBody(author: String, commentary: String): String {
        return gson.toJson(mapOf(
            "author" to author,
            "commentary" to commentary,
            "visibility" to "PUBLIC",
            "distribution" to mapOf(
                "feedDistribution" to "MAIN_FEED",
                "targetEntities" to emptyList<Any>(),
                "thirdPartyDistributionChannels" to emptyList<Any>(),
            ),
            "lifecycleState" to "PUBLISHED",
        ))
    }

    private fun publishTextPost(accessToken: String, author: String, content: PublishContent): PublishResult {
        val bodyMap = mutableMapOf<String, Any>(
            "author" to author,
            "commentary" to content.text,
            "visibility" to "PUBLIC",
            "distribution" to mapOf(
                "feedDistribution" to "MAIN_FEED",
                "targetEntities" to emptyList<Any>(),
                "thirdPartyDistributionChannels" to emptyList<Any>(),
            ),
            "lifecycleState" to "PUBLISHED",
        )
        if (content.linkUrl != null) {
            bodyMap["content"] = mapOf(
                "article" to mapOf(
                    "source" to content.linkUrl,
                    "title" to (content.title ?: ""),
                    "description" to (content.description ?: ""),
                )
            )
        }
        val body = gson.toJson(bodyMap)
        val response = executeLinkedInForHeaders(buildLinkedInPost("$API_BASE/rest/posts", accessToken, body))
        val postUrn = response.headers().firstValue("x-restli-id").orElse("")
        return PublishResult(
            success = true,
            platformPostId = postUrn,
            postUrl = postUrnToUrl(postUrn),
            publishedAt = Instant.now(),
        )
    }

    private fun publishImagePost(accessToken: String, author: String, content: PublishContent): PublishResult {
        val initBody = gson.toJson(mapOf(
            "initializeUploadRequest" to mapOf("owner" to author)
        ))
        val initData = linkedInPost("$API_BASE/rest/images?action=initializeUpload", accessToken, initBody)
        val value = initData.asJsonObject.getAsJsonObject("value")
        val uploadUrl = value.get("uploadUrl")?.asString
        val imageUrn = value.get("image")?.asString

        if (uploadUrl == null || imageUrn == null) {
            throw PublishError("Failed to initialize LinkedIn image upload", platformType.name, initData.toString())
        }

        val mediaSource = content.mediaUrls.first()
        uploadBinary(accessToken, uploadUrl, mediaSource)

        val bodyMap = mutableMapOf<String, Any>(
            "author" to author,
            "commentary" to content.text,
            "visibility" to "PUBLIC",
            "distribution" to mapOf(
                "feedDistribution" to "MAIN_FEED",
                "targetEntities" to emptyList<Any>(),
                "thirdPartyDistributionChannels" to emptyList<Any>(),
            ),
            "lifecycleState" to "PUBLISHED",
            "content" to mapOf("media" to mapOf("id" to imageUrn)),
        )
        val body = gson.toJson(bodyMap)
        val response = executeLinkedInForHeaders(buildLinkedInPost("$API_BASE/rest/posts", accessToken, body))
        val postUrn = response.headers().firstValue("x-restli-id").orElse("")
        return PublishResult(
            success = true,
            platformPostId = postUrn,
            postUrl = postUrnToUrl(postUrn),
            publishedAt = Instant.now(),
        )
    }

    private fun publishVideoPost(accessToken: String, author: String, content: PublishContent): PublishResult {
        val mediaSource = content.mediaUrls.first()
        val videoBytes = readMediaBytes(mediaSource)
        val fileSize = videoBytes.size.toLong()

        val initBody = gson.toJson(mapOf(
            "initializeUploadRequest" to mapOf(
                "owner" to author,
                "fileSizeBytes" to fileSize,
            )
        ))
        val initData = linkedInPost("$API_BASE/rest/videos?action=initializeUpload", accessToken, initBody)
        val value = initData.asJsonObject.getAsJsonObject("value")
        val videoUrn = value.get("video")?.asString
        val uploadInstructions = value.getAsJsonArray("uploadInstructions")
        val uploadToken = value.get("uploadToken")?.asString.orEmpty()

        if (videoUrn == null || uploadInstructions == null || uploadInstructions.size() == 0) {
            throw PublishError("Failed to initialize LinkedIn video upload", platformType.name, initData.toString())
        }

        val uploadedPartIds = mutableListOf<String>()
        for (instruction in uploadInstructions) {
            val instrObj = instruction.asJsonObject
            val chunkUrl = instrObj.get("uploadUrl").asString
            val firstByte = instrObj.get("firstByte").asLong.toInt()
            val lastByte = instrObj.get("lastByte").asLong.toInt()
            val chunk = videoBytes.copyOfRange(firstByte, lastByte + 1)
            val etag = uploadVideoChunk(chunkUrl, chunk)
            uploadedPartIds.add(etag)
        }

        val finalizeBody = gson.toJson(mapOf(
            "finalizeUploadRequest" to mapOf(
                "video" to videoUrn,
                "uploadToken" to uploadToken,
                "uploadedPartIds" to uploadedPartIds,
            )
        ))
        linkedInPost("$API_BASE/rest/videos?action=finalizeUpload", accessToken, finalizeBody)

        waitForVideoAvailable(accessToken, videoUrn)

        val bodyMap = mutableMapOf<String, Any>(
            "author" to author,
            "commentary" to content.text,
            "visibility" to "PUBLIC",
            "distribution" to mapOf(
                "feedDistribution" to "MAIN_FEED",
                "targetEntities" to emptyList<Any>(),
                "thirdPartyDistributionChannels" to emptyList<Any>(),
            ),
            "lifecycleState" to "PUBLISHED",
            "content" to mapOf("media" to mapOf("id" to videoUrn)),
        )
        val body = gson.toJson(bodyMap)
        val response = executeLinkedInForHeaders(buildLinkedInPost("$API_BASE/rest/posts", accessToken, body))
        val postUrn = response.headers().firstValue("x-restli-id").orElse("")
        return PublishResult(
            success = true,
            platformPostId = postUrn,
            postUrl = postUrnToUrl(postUrn),
            publishedAt = Instant.now(),
        )
    }

    private fun publishArticlePost(accessToken: String, author: String, content: PublishContent): PublishResult {
        val bodyMap = mutableMapOf<String, Any>(
            "author" to author,
            "commentary" to content.text,
            "visibility" to "PUBLIC",
            "distribution" to mapOf(
                "feedDistribution" to "MAIN_FEED",
                "targetEntities" to emptyList<Any>(),
                "thirdPartyDistributionChannels" to emptyList<Any>(),
            ),
            "lifecycleState" to "PUBLISHED",
            "content" to mapOf(
                "article" to mapOf(
                    "source" to (content.linkUrl ?: ""),
                    "title" to (content.title ?: ""),
                    "description" to (content.description ?: ""),
                )
            ),
        )
        val body = gson.toJson(bodyMap)
        val response = executeLinkedInForHeaders(buildLinkedInPost("$API_BASE/rest/posts", accessToken, body))
        val postUrn = response.headers().firstValue("x-restli-id").orElse("")
        return PublishResult(
            success = true,
            platformPostId = postUrn,
            postUrl = postUrnToUrl(postUrn),
            publishedAt = Instant.now(),
        )
    }

    @Suppress("UNCHECKED_CAST")
    private fun publishPollPost(accessToken: String, author: String, content: PublishContent): PublishResult {
        val pollQuestion = content.extra["poll_question"] as? String ?: content.text
        val pollOptions = content.extra["poll_options"] as? List<String> ?: emptyList()
        val pollDuration = content.extra["poll_duration"] as? String ?: "THREE_DAYS"

        if (pollOptions.isEmpty()) {
            throw PublishError("poll_options required in content.extra for LinkedIn poll posts", platformType.name)
        }

        val bodyMap = mutableMapOf<String, Any>(
            "author" to author,
            "commentary" to content.text,
            "visibility" to "PUBLIC",
            "distribution" to mapOf(
                "feedDistribution" to "MAIN_FEED",
                "targetEntities" to emptyList<Any>(),
                "thirdPartyDistributionChannels" to emptyList<Any>(),
            ),
            "lifecycleState" to "PUBLISHED",
            "content" to mapOf(
                "poll" to mapOf(
                    "question" to pollQuestion,
                    "options" to pollOptions.map { mapOf("text" to it) },
                    "settings" to mapOf("duration" to pollDuration),
                )
            ),
        )
        val body = gson.toJson(bodyMap)
        val response = executeLinkedInForHeaders(buildLinkedInPost("$API_BASE/rest/posts", accessToken, body))
        val postUrn = response.headers().firstValue("x-restli-id").orElse("")
        return PublishResult(
            success = true,
            platformPostId = postUrn,
            postUrl = postUrnToUrl(postUrn),
            publishedAt = Instant.now(),
        )
    }

    override fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult {
        val accessToken = account.metadata["accessToken"]
            ?: return PublishResult(success = false, errorMessage = "No access token")

        val profile = getProfile(account)
        val actor = "urn:li:person:${profile.platformUserId}"

        val body = gson.toJson(mapOf(
            "actor" to actor,
            "message" to mapOf("text" to comment),
        ))
        val url = "$API_BASE/rest/socialActions/${encodeUrn(postId)}/comments"
        val response = executeLinkedInForHeaders(buildLinkedInPost(url, accessToken, body))
        val commentUrn = response.headers().firstValue("x-restli-id").orElse("")
        return PublishResult(
            success = true,
            platformPostId = commentUrn,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.metadata["accessToken"] ?: return null
        val url = "$API_BASE/rest/organizationalEntityShareStatistics?q=organizationalEntity&shares[0]=$platformPostId"
        val data = linkedInGet(url, accessToken)
        val elements = data.asJsonObject.getAsJsonArray("elements")
        if (elements == null || elements.size() == 0) return null

        val stats = elements[0].asJsonObject.getAsJsonObject("totalShareStatistics")
        return PostInsights(
            platformPostId = platformPostId,
            impressions = stats?.get("impressionCount")?.asLong ?: 0,
            likes = stats?.get("likeCount")?.asLong ?: 0,
            comments = stats?.get("commentCount")?.asLong ?: 0,
            shares = stats?.get("shareCount")?.asLong ?: 0,
            clicks = stats?.get("clickCount")?.asLong ?: 0,
        )
    }

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.metadata["accessToken"] ?: return false
        return try {
            httpPostForm(REVOKE_URL, mapOf(
                "client_id" to (account.metadata["client_id"] ?: ""),
                "client_secret" to (account.metadata["client_secret"] ?: ""),
                "token" to accessToken,
            ))
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun uploadBinary(accessToken: String, uploadUrl: String, source: String) {
        val mediaBytes = readMediaBytes(source)
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(uploadUrl))
            .timeout(Duration.ofSeconds(120))
            .header("Authorization", "Bearer $accessToken")
            .header("Content-Type", "application/octet-stream")
        LINKEDIN_HEADERS.forEach { (k, v) -> requestBuilder.header(k, v) }
        val request = requestBuilder.PUT(HttpRequest.BodyPublishers.ofByteArray(mediaBytes)).build()
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() >= 400) {
            throw PublishError(
                "LinkedIn media upload failed: ${response.statusCode()}",
                platformType.name, response.body()
            )
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

    private fun uploadVideoChunk(uploadUrl: String, chunk: ByteArray): String {
        val request = HttpRequest.newBuilder()
            .uri(URI.create(uploadUrl))
            .timeout(Duration.ofSeconds(120))
            .header("Content-Type", "application/octet-stream")
            .PUT(HttpRequest.BodyPublishers.ofByteArray(chunk))
            .build()
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() >= 400) {
            throw PublishError(
                "LinkedIn video chunk upload failed: ${response.statusCode()}",
                platformType.name, response.body()
            )
        }
        var etag = response.headers().firstValue("etag").orElse("")
        if (etag.isEmpty()) {
            throw PublishError("LinkedIn video chunk upload succeeded but returned no ETag", platformType.name)
        }
        if (etag.length >= 2 && etag.startsWith("\"") && etag.endsWith("\"")) {
            etag = etag.substring(1, etag.length - 1)
        }
        return etag
    }

    private fun waitForVideoAvailable(
        accessToken: String,
        videoUrn: String,
        timeoutSeconds: Long = 180,
        pollIntervalMs: Long = 3000,
    ) {
        val deadline = System.nanoTime() + timeoutSeconds * 1_000_000_000
        var lastStatus: String? = null
        while (true) {
            val url = "$API_BASE/rest/videos/${encodeUrn(videoUrn)}"
            val data = linkedInGet(url, accessToken)
            val status = data.asJsonObject.get("status")?.asString
            if (status == "AVAILABLE") return
            if (status == "PROCESSING_FAILED") {
                val reason = data.asJsonObject.get("processingFailureReason")?.asString ?: "unknown"
                throw PublishError(
                    "LinkedIn rejected the video during processing: $reason",
                    platformType.name, data.toString()
                )
            }
            lastStatus = status
            if (System.nanoTime() >= deadline) {
                throw PublishError(
                    "Timed out waiting for LinkedIn video (last status: $lastStatus)",
                    platformType.name
                )
            }
            Thread.sleep(pollIntervalMs)
        }
    }

    private fun postUrnToUrl(urn: String): String? {
        if (urn.isEmpty()) return null
        val parts = urn.split(":")
        return if (parts.size >= 4) "https://www.linkedin.com/feed/update/$urn/" else null
    }
}
