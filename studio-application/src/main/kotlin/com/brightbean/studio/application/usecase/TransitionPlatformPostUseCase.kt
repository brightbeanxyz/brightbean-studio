package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class TransitionPlatformPostUseCase(
    private val platformPostRepository: PlatformPostRepository,
    private val postRepository: PostRepository,
) {
    fun execute(platformPostId: UUID, targetStatus: PlatformPostStatus, scheduledAt: Instant? = null): PlatformPost {
        val pp = platformPostRepository.findById(platformPostId)
            ?: throw IllegalArgumentException("PlatformPost not found: $platformPostId")

        val transitioned = pp.transitionTo(targetStatus)

        val updated = when (targetStatus) {
            PlatformPostStatus.SCHEDULED -> transitioned.copy(
                scheduledAt = scheduledAt ?: throw IllegalArgumentException("scheduledAt required for SCHEDULED"),
                updatedAt = Instant.now(),
            )
            PlatformPostStatus.DRAFT -> transitioned.copy(
                scheduledAt = null,
                updatedAt = Instant.now(),
            )
            PlatformPostStatus.PUBLISHED -> transitioned.copy(
                publishedAt = Instant.now(),
                updatedAt = Instant.now(),
            )
            else -> transitioned.copy(updatedAt = Instant.now())
        }

        platformPostRepository.update(updated)
        syncPostScheduledAt(pp.postId)
        return updated
    }

    private fun syncPostScheduledAt(postId: UUID) {
        val post = postRepository.findById(postId) ?: return
        val children = platformPostRepository.findByPostId(postId)
        val earliest = children.mapNotNull { it.scheduledAt }.minByOrNull { it }
        val updatedPost = post.copy(scheduledAt = earliest, updatedAt = Instant.now())
        postRepository.update(updatedPost)
    }
}
