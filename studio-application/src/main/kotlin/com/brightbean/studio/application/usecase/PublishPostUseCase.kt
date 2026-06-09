package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApprovalRequest
import com.brightbean.studio.domain.model.ApprovalStatus
import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.types.PublishContent
import java.time.Instant
import java.util.UUID

class PublishPostUseCase(
    private val postRepository: PostRepository,
    private val socialAccountRepository: SocialAccountRepository,
    private val platformPostRepository: PlatformPostRepository,
    private val providerRegistry: ProviderRegistry,
) {
    fun execute(postId: UUID): Post {
        val post = postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        val platformPosts = platformPostRepository.findByPostId(postId)
        val accounts = platformPosts.mapNotNull { pp ->
            socialAccountRepository.findById(pp.socialAccountId)
        }

        if (accounts.isEmpty()) {
            throw IllegalArgumentException("No social accounts found for post")
        }

        val now = Instant.now()
        var allSuccessful = true
        var firstError: String? = null

        for (account in accounts) {
            val provider = providerRegistry.get(account.platformType)
                ?: throw IllegalStateException("Provider not found: ${account.platformType}")

            val content = PublishContent(text = post.caption)
            val result: PublishResult = provider.publishPost(account, content)
            val existingPp = platformPosts.find { it.socialAccountId == account.id }

            if (existingPp != null) {
                val updated = existingPp.copy(
                    status = if (result.success) PlatformPostStatus.PUBLISHED else PlatformPostStatus.FAILED,
                    platformPostId = result.platformPostId ?: "",
                    publishError = result.errorMessage ?: "",
                    publishedAt = if (result.success) result.publishedAt else existingPp.publishedAt,
                    updatedAt = now,
                )
                platformPostRepository.update(updated)
            } else {
                val platformPost = PlatformPost(
                    id = UUID.randomUUID(),
                    postId = postId,
                    socialAccountId = account.id,
                    platformTitle = null,
                    platformCaption = null,
                    platformFirstComment = null,
                    platformMedia = null,
                    platformExtra = null,
                    status = if (result.success) PlatformPostStatus.PUBLISHED else PlatformPostStatus.FAILED,
                    platformPostId = result.platformPostId ?: "",
                    publishError = result.errorMessage ?: "",
                    publishedAt = result.publishedAt,
                    scheduledAt = null,
                    retryCount = 0,
                    nextRetryAt = null,
                    createdAt = now,
                    updatedAt = now,
                )
                platformPostRepository.save(platformPost)
            }

            if (!result.success) {
                allSuccessful = false
                firstError = firstError ?: result.errorMessage
            }
        }

        val updatedPost = post.copy(
            publishedAt = if (allSuccessful) now else post.publishedAt,
            updatedAt = now,
        )
        postRepository.update(updatedPost)

        return updatedPost
    }
}
