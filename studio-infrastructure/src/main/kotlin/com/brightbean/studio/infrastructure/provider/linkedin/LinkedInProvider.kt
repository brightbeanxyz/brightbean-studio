package com.brightbean.studio.infrastructure.provider.linkedin

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.infrastructure.provider.*

class LinkedInProvider : SocialProvider {
    override val platformType = PlatformType.LINKEDIN_COMPANY

    override fun authenticate(credential: Credential): AuthResult {
        return AuthResult(success = false, errorMessage = "Not implemented")
    }

    override fun refreshToken(credential: Credential): AuthResult {
        return AuthResult(success = false, errorMessage = "Not implemented")
    }

    override fun getProfile(socialAccount: SocialAccount): PlatformProfile {
        return PlatformProfile(
            platformUserId = socialAccount.platformUserId,
            platformUsername = socialAccount.platformUsername,
            platformDisplayName = socialAccount.platformDisplayName,
            platformAvatarUrl = socialAccount.platformAvatarUrl,
            profileUrl = socialAccount.profileUrl
        )
    }

    override fun publish(post: Post, socialAccount: SocialAccount): PublishResult {
        return PublishResult(success = false, errorMessage = "Not implemented")
    }

    override fun getComments(postId: String): List<Comment> {
        return emptyList()
    }

    override fun getInboxItems(socialAccount: SocialAccount): List<InboxItem> {
        return emptyList()
    }

    override fun getInsights(postId: String): PostInsights? {
        return null
    }
}
