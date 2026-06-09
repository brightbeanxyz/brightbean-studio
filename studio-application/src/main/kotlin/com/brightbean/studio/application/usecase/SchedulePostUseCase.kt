package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class SchedulePostUseCase(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {
    fun execute(postId: UUID, scheduledFor: Instant): Post {
        val post = postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        val now = Instant.now()
        val updatedPost = post.copy(
            scheduledAt = scheduledFor,
            updatedAt = now,
        )
        postRepository.update(updatedPost)

        val platformPosts = platformPostRepository.findByPostId(postId)
        for (pp in platformPosts) {
            val updated = pp.copy(
                status = PlatformPostStatus.SCHEDULED,
                scheduledAt = scheduledFor,
                updatedAt = now,
            )
            platformPostRepository.update(updated)
        }

        return updatedPost
    }
}
