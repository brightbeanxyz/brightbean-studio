package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Idea(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID,
    val title: String,
    val content: String,
    val createdAt: Instant,
)
