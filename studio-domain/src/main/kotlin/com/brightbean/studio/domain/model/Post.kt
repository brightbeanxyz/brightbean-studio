package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Post(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID?,
    val title: String,
    val caption: String,
    val firstComment: String,
    val internalNotes: String,
    val tags: List<String>,
    val categoryId: UUID?,
    val scheduledAt: Instant?,
    val publishedAt: Instant?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
