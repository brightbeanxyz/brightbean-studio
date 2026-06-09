package com.brightbean.studio.domain.model

import java.time.Instant
import java.time.LocalDate
import java.util.UUID

enum class RecurrenceFrequency {
    DAILY,
    WEEKLY,
    MONTHLY,
}

data class RecurrenceRule(
    val id: UUID,
    val postId: UUID,
    val frequency: RecurrenceFrequency,
    val interval: Int,
    val endDate: LocalDate?,
    val lastGeneratedAt: Instant?,
    val isActive: Boolean,
    val createdAt: Instant,
)
