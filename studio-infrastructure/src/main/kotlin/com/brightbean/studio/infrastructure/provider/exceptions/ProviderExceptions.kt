package com.brightbean.studio.infrastructure.provider.exceptions

open class ProviderError(
    message: String,
    val platform: String,
    val rawResponse: String? = null,
) : Exception(message)

class OAuthError(message: String, platform: String, rawResponse: String? = null) :
    ProviderError(message, platform, rawResponse)

class TokenExpiredError(message: String, platform: String, rawResponse: String? = null) :
    ProviderError(message, platform, rawResponse)

class RateLimitError(
    message: String,
    platform: String,
    val retryAfter: Int? = null,
    rawResponse: String? = null,
) : ProviderError(message, platform, rawResponse)

class PublishError(message: String, platform: String, rawResponse: String? = null) :
    ProviderError(message, platform, rawResponse)

class APIError(
    message: String,
    platform: String,
    val statusCode: Int,
    rawResponse: String? = null,
) : ProviderError(message, platform, rawResponse)
