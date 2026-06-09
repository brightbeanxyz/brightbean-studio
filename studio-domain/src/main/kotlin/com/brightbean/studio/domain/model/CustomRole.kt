package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class CustomRole(
    val id: UUID,
    val organizationId: UUID,
    val name: String,
    val permissions: Map<String, Boolean>,
    val createdAt: Instant,
    val updatedAt: Instant,
)
