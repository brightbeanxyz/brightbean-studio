package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Post(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID,
    val content: String,
    val platforms: List<PlatformType>,
    val categoryId: UUID?,
    val tags: List<Tag>,
    val status: PostStatus,
    val scheduledAt: Instant?,
    val publishedAt: Instant?,
    val mediaIds: List<UUID>,
    val createdAt: Instant,
    val updatedAt: Instant,
)
