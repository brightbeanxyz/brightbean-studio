package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Queue(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val categoryId: UUID?,
    val socialAccountId: UUID,
    val isActive: Boolean,
    val createdAt: Instant,
    val updatedAt: Instant,
)
