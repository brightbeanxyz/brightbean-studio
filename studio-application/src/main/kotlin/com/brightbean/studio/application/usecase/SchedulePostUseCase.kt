package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.PublishingQueue
import com.brightbean.studio.domain.model.QueueStatus
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.PublishingQueueRepository
import java.time.Instant
import java.util.UUID

class SchedulePostUseCase(
    private val postRepository: PostRepository,
    private val publishingQueueRepository: PublishingQueueRepository,
) {
    fun execute(postId: UUID, scheduledFor: Instant): PublishingQueue {
        val post = postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        if (post.status != PostStatus.SCHEDULED && post.status != PostStatus.DRAFT) {
            throw IllegalArgumentException("Post cannot be scheduled: ${post.status}")
        }

        val updatedPost = post.copy(
            status = PostStatus.SCHEDULED,
            scheduledAt = scheduledFor,
            updatedAt = Instant.now(),
        )
        postRepository.update(updatedPost)

        val queue = PublishingQueue(
            id = UUID.randomUUID(),
            workspaceId = post.workspaceId,
            postId = postId,
            scheduledFor = scheduledFor,
            attempts = 0,
            lastAttemptAt = null,
            status = QueueStatus.PENDING,
            errorMessage = null,
        )
        return publishingQueueRepository.save(queue)
    }
}
