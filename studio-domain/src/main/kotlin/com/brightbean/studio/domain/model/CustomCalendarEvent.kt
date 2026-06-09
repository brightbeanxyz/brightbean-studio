package com.brightbean.studio.domain.model

import java.time.Instant
import java.time.LocalDate
import java.util.UUID

data class CustomCalendarEvent(
    val id: UUID,
    val workspaceId: UUID,
    val title: String,
    val description: String,
    val startDate: LocalDate,
    val endDate: LocalDate,
    val color: String,
    val createdBy: UUID?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
