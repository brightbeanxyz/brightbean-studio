package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Organization(
    val id: UUID,
    val name: String,
    val logoUrl: String? = null,
    val defaultTimezone: String = "UTC",
    val billingEmail: String = "",
    val createdAt: Instant,
    val updatedAt: Instant,
)
