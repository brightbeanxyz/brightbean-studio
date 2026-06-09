package com.brightbean.studio.domain.model

import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.util.UUID

data class CalendarEntry(
    val id: UUID,
    val workspaceId: UUID,
    val postId: UUID?,
    val date: LocalDate,
    val timeSlots: List<TimeSlot>,
    val createdAt: Instant,
)

data class TimeSlot(
    val time: LocalTime,
    val socialAccountIds: List<UUID>,
    val status: SlotStatus,
)

enum class SlotStatus {
    FREE,
    RESERVED,
    PUBLISHED,
}
