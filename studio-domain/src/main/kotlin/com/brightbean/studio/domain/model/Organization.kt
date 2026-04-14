package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Organization(
    val id: UUID,
    val name: String,
    val description: String,
    val ownerId: UUID,
    val createdAt: Instant,
    val updatedAt: Instant,
)