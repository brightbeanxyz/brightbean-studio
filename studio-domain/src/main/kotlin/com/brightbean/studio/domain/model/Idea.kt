package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class IdeaStatus {
    UNASSIGNED,
    TODO,
    IN_PROGRESS,
    DONE,
}

data class Idea(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID?,
    val title: String,
    val description: String,
    val tags: List<String>,
    val mediaAssetId: UUID?,
    val status: IdeaStatus,
    val groupId: UUID?,
    val position: Int,
    val postId: UUID?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
