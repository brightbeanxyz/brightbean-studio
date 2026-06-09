package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class PostVersion(
    val id: UUID,
    val postId: UUID,
    val versionNumber: Int,
    val snapshot: String,
    val createdBy: UUID?,
    val createdAt: Instant,
)
