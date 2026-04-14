package com.brightbean.studio.infrastructure.provider

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.SocialAccount

interface SocialProvider {
    val platformType: PlatformType

    fun authenticate(credential: Credential): AuthResult
    fun refreshToken(credential: Credential): AuthResult
    fun getProfile(socialAccount: SocialAccount): PlatformProfile
    fun publish(post: Post, socialAccount: SocialAccount): PublishResult
    fun getComments(postId: String): List<Comment>
    fun getInboxItems(socialAccount: SocialAccount): List<InboxItem>
    fun getInsights(postId: String): PostInsights?
}
