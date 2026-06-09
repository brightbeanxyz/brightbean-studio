package com.brightbean.studio.application.worker

import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import java.time.Instant
import java.util.UUID

class PublishingWorker(
    private val platformPostRepository: PlatformPostRepository,
    private val publishPostUseCase: PublishPostUseCase,
) {
    fun processQueue() {
        val duePosts = platformPostRepository.findScheduledBefore(Instant.now())
        val processedPostIds = mutableSetOf<UUID>()
        for (platformPost in duePosts) {
            if (platformPost.postId !in processedPostIds) {
                processPost(platformPost.postId)
                processedPostIds.add(platformPost.postId)
            }
        }
    }

    fun processPost(postId: UUID) {
        try {
            publishPostUseCase.execute(postId)
        } catch (_: Exception) {
            val platformPosts = platformPostRepository.findByPostId(postId)
            for (pp in platformPosts) {
                if (pp.status == PlatformPostStatus.SCHEDULED) {
                    val updated = pp.copy(
                        status = PlatformPostStatus.FAILED,
                        publishError = "Publishing failed",
                        retryCount = pp.retryCount + 1,
                        updatedAt = Instant.now(),
                    )
                    platformPostRepository.update(updated)
                }
            }
        }
    }

    companion object {
        const val MAX_ATTEMPTS = 3
    }
}
