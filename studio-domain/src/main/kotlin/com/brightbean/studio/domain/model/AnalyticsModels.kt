package com.brightbean.studio.domain.model

import java.time.Instant
import java.time.LocalDate
import java.util.UUID

data class AccountInsightsSnapshot(
    val id: UUID,
    val socialAccountId: UUID,
    val metricKey: String,
    val date: LocalDate,
    val value: Double,
    val capturedAt: Instant,
)

data class PostInsightsSnapshot(
    val id: UUID,
    val platformPostId: UUID,
    val metricKey: String,
    val date: LocalDate,
    val value: Double,
    val capturedAt: Instant,
)
