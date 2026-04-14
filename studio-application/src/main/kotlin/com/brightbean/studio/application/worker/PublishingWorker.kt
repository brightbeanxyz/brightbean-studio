package com.brightbean.studio.application.worker

import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.domain.model.QueueStatus
import com.brightbean.studio.domain.repository.PublishingQueueRepository
import java.time.Instant
import java.util.UUID

class PublishingWorker(
    private val publishingQueueRepository: PublishingQueueRepository,
    private val publishPostUseCase: PublishPostUseCase,
) {
    fun processQueue() {
        val pendingItems = publishingQueueRepository.findPending()
        for (item in pendingItems) {
            processItem(item.id)
        }
    }

    fun processItem(queueId: UUID) {
        val queueItem = publishingQueueRepository.findById(queueId) ?: return

        val processingItem = queueItem.copy(
            status = QueueStatus.PROCESSING,
            lastAttemptAt = Instant.now(),
        )
        publishingQueueRepository.update(processingItem)

        try {
            publishPostUseCase.execute(queueItem.postId)
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