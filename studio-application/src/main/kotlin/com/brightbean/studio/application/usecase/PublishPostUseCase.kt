package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.PublishResult
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

        if (post.status == PostStatus.PENDING_APPROVAL) {
            throw IllegalArgumentException("Post requires approval before publishing")
        }

        val socialAccounts = post.platforms.flatMap { platform ->
            socialAccountRepository.findActiveByWorkspace(post.workspaceId)
                .filter { it.platformType == platform }
        }

        if (socialAccounts.isEmpty()) {
            throw IllegalArgumentException("No active social accounts found for post platforms")
        }

        val now = Instant.now()
        var allSuccessful = true
        var firstError: String? = null

        for (account in socialAccounts) {
            val provider = providerRegistry.get(account.platformType)
                ?: throw IllegalStateException("Provider not found: ${account.platformType}")

            val result: PublishResult = provider.publish(post, account)
            val platformPost = PlatformPost(
                id = UUID.randomUUID(),
                postId = postId,
                socialAccountId = account.id,
                platformPostId = result.platformPostId,
                platformUrl = result.postUrl,
                status = if (result.success) PostStatus.PUBLISHED else PostStatus.FAILED,
                errorMessage = result.errorMessage,
                publishedAt = result.publishedAt,
            )
            platformPostRepository.save(platformPost)

            if (!result.success) {
                allSuccessful = false
                firstError = firstError ?: result.errorMessage
            }
        }

        val updatedStatus = if (allSuccessful) PostStatus.PUBLISHED else PostStatus.FAILED
        val updatedPost = post.copy(
            status = updatedStatus,
            publishedAt = if (allSuccessful) now else post.publishedAt,
            updatedAt = now,
        )
        postRepository.update(updatedPost)

        return updatedPost
    }
}
