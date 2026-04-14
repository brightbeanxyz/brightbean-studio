package com.brightbean.studio.application.worker

import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.PublishingQueue
import com.brightbean.studio.domain.model.QueueStatus
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.PublishingQueueRepository
import java.time.Instant
import java.util.UUID

class TaskScheduler(
    private val postRepository: PostRepository,
    private val publishingQueueRepository: PublishingQueueRepository,
) {
    fun schedulePost(postId: UUID, scheduledFor: Instant): PublishingQueue {
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

    fun processDueTasks() {
        val now = Instant.now()
        val allPending = publishingQueueRepository.findPending()
        val dueTasks = allPending.filter { it.scheduledFor <= now }
        for (task in dueTasks) {
            processTask(task.id)
        }
    }

    fun processTask(queueId: UUID) {
        val queueItem = publishingQueueRepository.findById(queueId) ?: return

        val processingItem = queueItem.copy(
            status = QueueStatus.PROCESSING,
            lastAttemptAt = Instant.now(),
        )
        publishingQueueRepository.update(processingItem)

        try {
            val post = postRepository.findById(queueItem.postId)
                ?: throw IllegalArgumentException("Post not found: ${queueItem.postId}")
            val updatedPost = post.copy(
                status = PostStatus.PUBLISHED,
                publishedAt = Instant.now(),
                updatedAt = Instant.now(),
            )
            postRepository.update(updatedPost)
            val completedItem = processingItem.copy(status = QueueStatus.COMPLETED)
            publishingQueueRepository.update(completedItem)
        } catch (e: Exception) {
            val attempts = queueItem.attempts + 1
            if (attempts >= MAX_ATTEMPTS) {
                val failedItem = processingItem.copy(
                    status = QueueStatus.FAILED,
                    attempts = attempts,
                    errorMessage = e.message,
                )
                publishingQueueRepository.update(failedItem)
            } else {
                val retryItem = processingItem.copy(
                    attempts = attempts,
                    status = QueueStatus.PENDING,
                    errorMessage = e.message,
                )
                publishingQueueRepository.update(retryItem)
            }
        }
    }

    companion object {
        const val MAX_ATTEMPTS = 3
    }
}