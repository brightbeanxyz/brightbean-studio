package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class QueueEntry(
    val id: UUID,
    val queueId: UUID,
    val postId: UUID,
    val position: Int,
    val assignedSlotDatetime: Instant?,
    val createdAt: Instant,
)
