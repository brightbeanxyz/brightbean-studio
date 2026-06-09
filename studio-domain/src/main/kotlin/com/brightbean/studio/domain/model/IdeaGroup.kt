package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class IdeaGroup(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val position: Int,
    val createdAt: Instant,
    val updatedAt: Instant,
)
