package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class PostTemplate(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val description: String,
    val templateData: String,
    val createdBy: UUID?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
