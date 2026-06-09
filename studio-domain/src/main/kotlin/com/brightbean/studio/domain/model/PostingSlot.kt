package com.brightbean.studio.domain.model

import java.time.Instant
import java.time.LocalTime
import java.util.UUID

data class PostingSlot(
    val id: UUID,
    val socialAccountId: UUID,
    val dayOfWeek: Int,
    val time: LocalTime,
    val isActive: Boolean,
    val createdAt: Instant,
    val updatedAt: Instant,
)
