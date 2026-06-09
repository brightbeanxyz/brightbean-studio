package com.brightbean.studio.infrastructure.provider

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.types.*

interface SocialProvider {
    val platformType: PlatformType
    val authType: AuthType get() = AuthType.OAUTH2
    val maxCaptionLength: Int get() = 2200
    val supportedPostTypes: List<PostType> get() = listOf(PostType.TEXT)
    val supportedMediaTypes: List<MediaType> get() = listOf(MediaType.JPEG, MediaType.PNG)
    val requiredScopes: List<String> get() = emptyList()
    val rateLimits: RateLimitConfig get() = RateLimitConfig()

    fun getAuthUrl(clientId: String, redirectUri: String, state: String): String =
        throw NotImplementedError("getAuthUrl not implemented for ${platformType.name}")

    fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens =
        throw NotImplementedError("exchangeCode not implemented for ${platformType.name}")

    fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens =
        throw NotImplementedError("refreshToken not implemented for ${platformType.name}")

    fun getProfile(account: SocialAccount): PlatformProfile
    fun publishPost(account: SocialAccount, content: PublishContent): PublishResult

    fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult =
        PublishResult(success = false, errorMessage = "Comments not supported for ${platformType.name}")

    fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? = null
    fun getAccountMetrics(account: SocialAccount): AccountMetrics = AccountMetrics()
    fun getInboxItems(account: SocialAccount): List<InboxItem>
    fun revokeToken(account: SocialAccount): Boolean = false

    @Deprecated("Use exchangeCode instead", ReplaceWith("exchangeCode(code, clientId, clientSecret, redirectUri)"))
    fun authenticate(credential: Credential): AuthResult =
        throw NotImplementedError("Use exchangeCode instead")

    @Deprecated("Use refreshToken(String, String, String) instead")
    fun refreshToken(credential: Credential): AuthResult =
        throw NotImplementedError("Use refreshToken(refreshToken, clientId, clientSecret) instead")

    @Deprecated("Use publishPost instead", ReplaceWith("publishPost(account, content)"))
    fun publish(post: Post, socialAccount: SocialAccount): PublishResult =
        publishPost(socialAccount, PublishContent(text = post.content))

    @Deprecated("No longer part of the provider interface")
    fun getComments(postId: String): List<Comment> = emptyList()

    @Deprecated("Use getPostMetrics instead", ReplaceWith("getPostMetrics(account, platformPostId)"))
    fun getInsights(postId: String): PostInsights? = null
}
