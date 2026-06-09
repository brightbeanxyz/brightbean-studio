package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.types.PublishContent
import java.time.Instant
import java.util.UUID

class PublishPostUseCase(
    private val postRepository: PostRepository,
    private val socialAccountRepository: SocialAccountRepository,
    private val platformPostRepository: PlatformPostRepository,
    private val providerRegistry: ProviderRegistry,
) {
    data class PlatformResult(
        val platformPostId: UUID,
        val success: Boolean,
        val platformPostPlatformId: String,
        val errorMessage: String,
    )

    fun execute(postId: UUID): List<PlatformResult> {
        val post = postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        val platformPosts = platformPostRepository.findByPostId(postId)
            .filter { it.status == PlatformPostStatus.SCHEDULED || it.status == PlatformPostStatus.PUBLISHING }

        if (platformPosts.isEmpty()) {
            throw IllegalArgumentException("No schedulable platform posts found for post: $postId")
        }

        return platformPosts.map { pp ->
            val account = socialAccountRepository.findById(pp.socialAccountId)
            if (account == null) {
                val failed = pp.transitionTo(PlatformPostStatus.FAILED)
                val updatedPp = failed.copy(
                    publishError = "Social account not found: ${pp.socialAccountId}",
                    updatedAt = Instant.now(),
                )
                platformPostRepository.update(updatedPp)
                return@map PlatformResult(
                    platformPostId = pp.id,
                    success = false,
                    platformPostPlatformId = "",
                    errorMessage = "Social account not found: ${pp.socialAccountId}",
                )
            }

            try {
                val transitioned = pp.transitionTo(PlatformPostStatus.PUBLISHING)
                platformPostRepository.update(transitioned)

                val provider = providerRegistry.get(account.platformType)
                    ?: throw IllegalStateException("Provider not found for platform: ${account.platformType}")

                val content = PublishContent(text = post.caption)
                val result = provider.publishPost(account, content)

                if (result.success) {
                    val published = transitioned.transitionTo(PlatformPostStatus.PUBLISHED)
                    val updatedPp = published.copy(
                        platformPostId = result.platformPostId ?: "",
                        publishedAt = result.publishedAt ?: Instant.now(),
                        updatedAt = Instant.now(),
                    )
                    platformPostRepository.update(updatedPp)

                    PlatformResult(
                        platformPostId = pp.id,
                        success = true,
                        platformPostPlatformId = result.platformPostId ?: "",
                        errorMessage = "",
                    )
                } else {
                    val failed = transitioned.transitionTo(PlatformPostStatus.FAILED)
                    val updatedPp = failed.copy(
                        publishError = result.errorMessage ?: "Unknown error",
                        updatedAt = Instant.now(),
                    )
                    platformPostRepository.update(updatedPp)

                    PlatformResult(
                        platformPostId = pp.id,
                        success = false,
                        platformPostPlatformId = "",
                        errorMessage = result.errorMessage ?: "Unknown error",
                    )
                }
            } catch (e: Exception) {
                val failed = pp.transitionTo(PlatformPostStatus.FAILED)
                val updatedPp = failed.copy(
                    publishError = e.message ?: "Unknown error",
                    updatedAt = Instant.now(),
                )
                platformPostRepository.update(updatedPp)

                PlatformResult(
                    platformPostId = pp.id,
                    success = false,
                    platformPostPlatformId = "",
                    errorMessage = e.message ?: "Unknown error",
                )
            }
        }
    }
}
