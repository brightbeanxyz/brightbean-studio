package com.brightbean.studio.infrastructure.provider.types

enum class AuthType { OAUTH2, SESSION, INSTANCE_OAUTH }

enum class PostType {
    TEXT, IMAGE, VIDEO, CAROUSEL, STORY, REEL, LINK, ARTICLE, POLL, PIN, SHORT
}

enum class MediaType { JPEG, PNG, GIF, MP4, MOV, WEBP, PDF }

data class OAuthTokens(
    val accessToken: String,
    val refreshToken: String? = null,
    val expiresIn: Long? = null,
)

data class PublishContent(
    val text: String = "",
    val mediaUrls: List<String> = emptyList(),
    val postType: PostType = PostType.TEXT,
    val linkUrl: String? = null,
    val title: String? = null,
    val description: String? = null,
    val firstComment: String? = null,
    val extra: Map<String, Any> = emptyMap(),
)

data class RateLimitConfig(
    val callsPerHour: Int = 200,
    val callsPerDay: Int = 5000,
    val publishPerDay: Int = 25,
)

data class AccountMetrics(
    val followers: Long = 0,
    val following: Long = 0,
    val posts: Long = 0,
    val engagementRate: Double = 0.0,
    val extra: Map<String, Any> = emptyMap(),
)
