package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class PublishingQueue(
    val id: UUID,
    val workspaceId: UUID,
    val postId: UUID,
    val scheduledFor: Instant,
    val attempts: Int,
    val lastAttemptAt: Instant?,
    val status: QueueStatus,
    val errorMessage: String?,
)

enum class QueueStatus {
    PENDING,
    PROCESSING,
    COMPLETED,
    FAILED,
    CANCELLED,
}
