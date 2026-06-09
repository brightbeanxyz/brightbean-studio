package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class SchedulePostUseCase(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {
    fun execute(postId: UUID, scheduledAt: Instant) {
        val post = postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        val updatedPost = post.copy(scheduledAt = scheduledAt, updatedAt = Instant.now())
        postRepository.update(updatedPost)

        val platformPosts = platformPostRepository.findByPostId(postId)
        for (pp in platformPosts) {
            if (pp.status.canTransitionTo(PlatformPostStatus.SCHEDULED)) {
                val scheduled = pp.transitionTo(PlatformPostStatus.SCHEDULED).copy(
                    scheduledAt = scheduledAt,
                    updatedAt = Instant.now(),
                )
                platformPostRepository.update(scheduled)
            }
        }
    }
}
