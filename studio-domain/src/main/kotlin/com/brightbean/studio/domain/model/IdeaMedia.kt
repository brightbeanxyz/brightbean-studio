package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class IdeaMedia(
    val id: UUID,
    val ideaId: UUID,
    val mediaAssetId: UUID,
    val position: Int,
    val createdAt: Instant,
    val updatedAt: Instant,
)
