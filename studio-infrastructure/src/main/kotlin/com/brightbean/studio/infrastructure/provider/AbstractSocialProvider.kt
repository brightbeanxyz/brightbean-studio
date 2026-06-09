package com.brightbean.studio.infrastructure.provider

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.exceptions.*
import com.brightbean.studio.infrastructure.provider.types.*
import com.google.gson.Gson
import com.google.gson.JsonElement
import com.google.gson.JsonParser
import java.net.URI
import java.net.URLEncoder
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Duration

abstract class AbstractSocialProvider(
    override val platformType: PlatformType,
    override val authType: AuthType,
    override val maxCaptionLength: Int,
    override val supportedPostTypes: List<PostType>,
    override val supportedMediaTypes: List<MediaType>,
    override val requiredScopes: List<String>,
    override val rateLimits: RateLimitConfig = RateLimitConfig(),
) : SocialProvider {

    protected val httpClient: HttpClient = HttpClient.newBuilder()
        .connectTimeout(Duration.ofSeconds(30))
        .followRedirects(HttpClient.Redirect.NORMAL)
        .build()

    protected val gson = Gson()

    protected fun httpGet(url: String, accessToken: String? = null): JsonElement {
        val request = buildRequest(url, "GET", accessToken)
        return executeRequest(request)
    }

    protected fun httpPost(
        url: String,
        body: String? = null,
        accessToken: String? = null,
        contentType: String = "application/json",
    ): JsonElement {
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(60))
            .header("Content-Type", contentType)
        if (accessToken != null) requestBuilder.header("Authorization", "Bearer $accessToken")
        val publisher =
            if (body != null) HttpRequest.BodyPublishers.ofString(body) else HttpRequest.BodyPublishers.noBody()
        val request = requestBuilder.POST(publisher).build()
        return executeRequest(request)
    }

    protected fun httpPostForm(url: String, formData: Map<String, String>, accessToken: String? = null): JsonElement {
        val formBody = formData.entries.joinToString("&") {
            "${it.key}=${URLEncoder.encode(it.value, "UTF-8")}"
        }
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(60))
            .header("Content-Type", "application/x-www-form-urlencoded")
        if (accessToken != null) requestBuilder.header("Authorization", "Bearer $accessToken")
        val request = requestBuilder.POST(HttpRequest.BodyPublishers.ofString(formBody)).build()
        return executeRequest(request)
    }

    protected fun httpPut(
        url: String,
        body: ByteArray,
        accessToken: String? = null,
        contentType: String = "application/octet-stream",
    ): HttpResponse<ByteArray> {
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(120))
            .header("Content-Type", contentType)
        if (accessToken != null) requestBuilder.header("Authorization", "Bearer $accessToken")
        val request = requestBuilder.PUT(HttpRequest.BodyPublishers.ofByteArray(body)).build()
        return httpClient.send(request, HttpResponse.BodyHandlers.ofByteArray())
    }

    protected fun httpPutJson(url: String, body: String, accessToken: String? = null): JsonElement {
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(60))
            .header("Content-Type", "application/json")
        if (accessToken != null) requestBuilder.header("Authorization", "Bearer $accessToken")
        val request = requestBuilder.PUT(HttpRequest.BodyPublishers.ofString(body)).build()
        return executeRequest(request)
    }

    protected fun httpDelete(url: String, accessToken: String? = null): JsonElement? {
        val requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(30))
        if (accessToken != null) requestBuilder.header("Authorization", "Bearer $accessToken")
        val request = requestBuilder.DELETE().build()
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() == 204) return null
        return handleResponse(response)
    }

    private fun buildRequest(url: String, method: String, accessToken: String?): HttpRequest {
        val builder = HttpRequest.newBuilder()
            .uri(URI.create(url))
            .timeout(Duration.ofSeconds(30))
        if (accessToken != null) builder.header("Authorization", "Bearer $accessToken")
        builder.method(method, HttpRequest.BodyPublishers.noBody())
        return builder.build()
    }

    private fun executeRequest(request: HttpRequest): JsonElement {
        val response = httpClient.send(request, HttpResponse.BodyHandlers.ofString())
        return handleResponse(response)
    }

    private fun handleResponse(response: HttpResponse<String>): JsonElement {
        val statusCode = response.statusCode()
        val body = response.body()

        if (statusCode == 429) {
            val retryAfter = response.headers().firstValue("Retry-After").orElse(null)?.toIntOrNull()
            throw RateLimitError("Rate limit exceeded", platformType.name, retryAfter, body)
        }

        if (statusCode in 400..499) {
            throw APIError("API error: $body", platformType.name, statusCode, body)
        }

        if (statusCode in 500..599) {
            throw APIError("Server error: $body", platformType.name, statusCode, body)
        }

        return if (body.isBlank()) JsonParser.parseString("{}") else JsonParser.parseString(body)
    }

    override fun getInboxItems(account: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> =
        emptyList()

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult =
        PublishResult(success = false, errorMessage = "Not implemented for ${platformType.name}")
}
