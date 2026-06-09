package com.brightbean.studio.infrastructure.provider.google_business

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.AbstractSocialProvider
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.PostInsights
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.exceptions.OAuthError
import com.brightbean.studio.infrastructure.provider.exceptions.PublishError
import com.brightbean.studio.infrastructure.provider.types.*
import java.net.URLEncoder
import java.time.Instant

class GoogleBusinessProvider : AbstractSocialProvider(
    platformType = PlatformType.GOOGLE_BUSINESS,
    authType = AuthType.OAUTH2,
    maxCaptionLength = 1500,
    supportedPostTypes = listOf(PostType.TEXT, PostType.IMAGE),
    supportedMediaTypes = listOf(MediaType.JPEG, MediaType.PNG),
    requiredScopes = listOf("https://www.googleapis.com/auth/business.manage"),
) {
    companion object {
        private const val AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
        private const val TOKEN_URL = "https://oauth2.googleapis.com/token"
        private const val REVOKE_URL = "https://oauth2.googleapis.com/revoke"
        private const val ACCOUNTS_API = "https://mybusinessaccountmanagement.googleapis.com/v1"
        private const val BUSINESS_INFO_API = "https://mybusinessbusinessinformation.googleapis.com/v1"
        private const val POSTS_API = "https://mybusiness.googleapis.com/v4"
    }

    override fun getAuthUrl(clientId: String, redirectUri: String, state: String): String {
        val scope = requiredScopes.joinToString(" ")
        return "$AUTH_URL?client_id=$clientId&redirect_uri=${URLEncoder.encode(redirectUri, "UTF-8")}" +
            "&response_type=code&scope=${URLEncoder.encode(scope, "UTF-8")}&state=$state" +
            "&access_type=offline&prompt=consent"
    }

    override fun exchangeCode(code: String, clientId: String, clientSecret: String, redirectUri: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "client_id" to clientId,
            "client_secret" to clientSecret,
            "code" to code,
            "redirect_uri" to redirectUri,
            "grant_type" to "authorization_code",
        ))
        val obj = data.asJsonObject
        if (obj.has("error")) {
            val desc = obj.get("error_description")?.asString ?: obj.get("error").asString
            throw OAuthError("Token exchange failed: $desc", platformType.name, data.toString())
        }
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = obj.get("refresh_token")?.asString,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun refreshToken(refreshToken: String, clientId: String, clientSecret: String): OAuthTokens {
        val data = httpPostForm(TOKEN_URL, mapOf(
            "client_id" to clientId,
            "client_secret" to clientSecret,
            "refresh_token" to refreshToken,
            "grant_type" to "refresh_token",
        ))
        val obj = data.asJsonObject
        if (obj.has("error")) {
            val desc = obj.get("error_description")?.asString ?: obj.get("error").asString
            throw OAuthError("Token refresh failed: $desc", platformType.name, data.toString())
        }
        return OAuthTokens(
            accessToken = obj.get("access_token").asString,
            refreshToken = refreshToken,
            expiresIn = obj.get("expires_in")?.asLong,
        )
    }

    override fun revokeToken(account: SocialAccount): Boolean {
        val accessToken = account.accessToken ?: return false
        return try {
            httpPostForm(REVOKE_URL, mapOf("token" to accessToken))
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun getAccountId(accessToken: String): String {
        val data = httpGet("$ACCOUNTS_API/accounts", accessToken)
        val accounts = data.asJsonObject.getAsJsonArray("accounts")
        if (accounts == null || accounts.size() == 0) {
            throw PublishError("No Google Business accounts found", platformType.name)
        }
        return accounts[0].asJsonObject.get("name").asString
    }

    private fun getLocationId(accessToken: String, accountId: String): String {
        val data = httpGet("$BUSINESS_INFO_API/$accountId/locations", accessToken)
        val locations = data.asJsonObject.getAsJsonArray("locations")
        if (locations == null || locations.size() == 0) {
            throw PublishError("No locations found for Google Business account", platformType.name)
        }
        return locations[0].asJsonObject.get("name").asString
    }

    override fun getProfile(account: SocialAccount): PlatformProfile {
        val accessToken = account.accessToken
            ?: return PlatformProfile(
                platformUserId = account.platformUserId,
                platformUsername = account.platformUsername,
                platformDisplayName = account.platformDisplayName,
                platformAvatarUrl = account.platformAvatarUrl,
                profileUrl = account.profileUrl,
            )

        val accountId = getAccountId(accessToken)
        val data = httpGet("$BUSINESS_INFO_API/$accountId/locations", accessToken)
        val locations = data.asJsonObject.getAsJsonArray("locations")

        if (locations != null && locations.size() > 0) {
            val loc = locations[0].asJsonObject
            val name = loc.get("title")?.asString ?: loc.get("name")?.asString ?: ""
            val addressObj = loc.getAsJsonObject("storefrontAddress")
            val addressLines = addressObj?.getAsJsonArray("addressLines")
            val address = addressLines?.joinToString(", ") { it.asString } ?: ""
            val phone = loc.getAsJsonObject("phoneNumbers")?.get("primaryPhone")?.asString ?: ""

            return PlatformProfile(
                platformUserId = loc.get("name")?.asString ?: accountId,
                platformUsername = account.platformUsername,
                platformDisplayName = name,
                profileUrl = account.profileUrl,
                metadata = mapOf(
                    "address" to address,
                    "phone" to phone,
                ),
            )
        }

        return PlatformProfile(
            platformUserId = accountId,
            platformUsername = account.platformUsername,
            platformDisplayName = accountId,
            profileUrl = account.profileUrl,
        )
    }

    override fun publishPost(account: SocialAccount, content: PublishContent): PublishResult {
        val accessToken = account.accessToken
            ?: return PublishResult(success = false, errorMessage = "No access token")

        if (content.text.length > maxCaptionLength) {
            throw PublishError(
                "Post text exceeds $maxCaptionLength characters (got ${content.text.length})",
                platformType.name,
            )
        }

        val accountId = getAccountId(accessToken)
        val locationId = getLocationId(accessToken, accountId)

        @Suppress("UNCHECKED_CAST")
        val topicType = (content.extra["topic_type"] as? String) ?: "STANDARD"
        @Suppress("UNCHECKED_CAST")
        val languageCode = (content.extra["language_code"] as? String) ?: "en"

        val bodyMap = mutableMapOf<String, Any>(
            "languageCode" to languageCode,
            "summary" to content.text,
            "topicType" to topicType,
        )

        if (content.mediaUrls.isNotEmpty()) {
            bodyMap["media"] = content.mediaUrls.map { url ->
                mapOf("mediaFormat" to "PHOTO", "sourceUrl" to url)
            }
        }

        @Suppress("UNCHECKED_CAST")
        if (topicType == "EVENT") {
            val event = content.extra["event"] as? Map<String, Any>
            if (event != null) bodyMap["event"] = event
        }

        @Suppress("UNCHECKED_CAST")
        if (topicType == "OFFER") {
            val offer = content.extra["offer"] as? Map<String, Any>
            if (offer != null) bodyMap["offer"] = offer
        }

        val body = gson.toJson(bodyMap)
        val data = httpPost("$POSTS_API/$locationId/localPosts", body, accessToken)
        val obj = data.asJsonObject
        val postName = obj.get("name")?.asString ?: ""

        return PublishResult(
            success = true,
            platformPostId = postName,
            postUrl = obj.get("searchUrl")?.asString,
            publishedAt = Instant.now(),
        )
    }

    override fun getPostMetrics(account: SocialAccount, platformPostId: String): PostInsights? {
        val accessToken = account.accessToken ?: return null
        val data = httpGet("$POSTS_API/$platformPostId", accessToken)
        val obj = data.asJsonObject

        var searchViews = 0L
        val metrics = obj.getAsJsonArray("searchActionMetrics")
        if (metrics != null) {
            for (metric in metrics) {
                val m = metric.asJsonObject
                if (m.get("metricType")?.asString == "QUERIES_DIRECT") {
                    searchViews += m.get("value")?.asLong ?: 0
                }
            }
        }

        return PostInsights(
            platformPostId = platformPostId,
            impressions = searchViews,
        )
    }
}
