package com.brightbean.studio.application.worker

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class TaskScheduler(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {
    fun schedulePost(postId: UUID, scheduledFor: Instant): Post {
        val post = postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        val updatedPost = post.copy(
            scheduledAt = scheduledFor,
            updatedAt = Instant.now(),
        )
        postRepository.update(updatedPost)

        val platformPosts = platformPostRepository.findByPostId(postId)
        for (pp in platformPosts) {
            val updated = pp.copy(
                status = PlatformPostStatus.SCHEDULED,
                scheduledAt = scheduledFor,
                updatedAt = Instant.now(),
            )
            platformPostRepository.update(updated)
        }

        return updatedPost
    }

    fun processDueTasks() {
        val now = Instant.now()
        val scheduled = platformPostRepository.findScheduledBefore(now)
        val processedPostIds = mutableSetOf<UUID>()
        for (pp in scheduled) {
            if (pp.postId !in processedPostIds) {
                processTask(pp.postId)
                processedPostIds.add(pp.postId)
            }
        }
    }

    fun processTask(postId: UUID) {
        val post = postRepository.findById(postId) ?: return
        val platformPosts = platformPostRepository.findByPostId(postId)

        for (pp in platformPosts) {
            if (pp.status != PlatformPostStatus.SCHEDULED) continue

            val now = Instant.now()
            val newRetryCount = pp.retryCount + 1
            if (newRetryCount >= MAX_ATTEMPTS) {
                val failed = pp.copy(
                    status = PlatformPostStatus.FAILED,
                    retryCount = newRetryCount,
                    publishError = "Max retries exceeded",
                    updatedAt = now,
                )
                platformPostRepository.update(failed)
            } else {
                val retry = pp.copy(
                    retryCount = newRetryCount,
                    updatedAt = now,
                )
                platformPostRepository.update(retry)
            }
        }
    }

    companion object {
        const val MAX_ATTEMPTS = 3
    }
}
