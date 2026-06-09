package com.brightbean.studio.infrastructure.provider.linkedin

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.types.*
import com.google.gson.JsonParser

class LinkedInPersonalProvider(
    private val oauthMode: String = "oidc",
) : LinkedInProvider(platformType = PlatformType.LINKEDIN_PERSONAL) {

    override val requiredScopes: List<String> = if (isOidcMode) {
        listOf("openid", "profile", "email", "w_member_social")
    } else {
        listOf("r_basicprofile", "w_member_social", "r_member_social")
    }

    private val isOidcMode: Boolean get() = oauthMode == "oidc"

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.metadata["accessToken"]
            ?: return PlatformProfile(
                platformUserId = account.platformUserId,
                platformUsername = account.platformUsername,
                platformDisplayName = account.platformDisplayName,
                platformAvatarUrl = account.platformAvatarUrl,
                profileUrl = account.profileUrl,
            )

        if (!isOidcMode) return super.getProfile(account)

        val url = "$API_BASE/v2/userinfo"
        val request = java.net.http.HttpRequest.newBuilder()
            .uri(java.net.URI.create(url))
            .timeout(java.time.Duration.ofSeconds(30))
            .header("Authorization", "Bearer $accessToken")
            .GET()
            .build()
        val response = httpClient.send(request, java.net.http.HttpResponse.BodyHandlers.ofString())
        if (response.statusCode() >= 400) {
            throw com.brightbean.studio.infrastructure.provider.exceptions.APIError(
                "LinkedIn userinfo failed: ${response.body()}",
                platformType.name, response.statusCode(), response.body()
            )
        }
        val data = JsonParser.parseString(response.body()).asJsonObject

        return PlatformProfile(
            platformUserId = data.get("sub")?.asString ?: account.platformUserId,
            platformUsername = account.platformUsername,
            platformDisplayName = data.get("name")?.asString ?: account.platformDisplayName,
            platformAvatarUrl = data.get("picture")?.asString ?: account.platformAvatarUrl,
            profileUrl = account.profileUrl,
        )
    }

    override fun publishComment(account: SocialAccount, postId: String, comment: String): PublishResult {
        if (isOidcMode) {
            return PublishResult(
                success = false,
                errorMessage = "First comment is unsupported in OIDC mode: socialActions.CREATE requires Community Management API approval."
            )
        }
        return super.publishComment(account, postId, comment)
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String) = null

    override fun getAccountMetrics(account: SocialAccount): AccountMetrics =
        AccountMetrics()
}
