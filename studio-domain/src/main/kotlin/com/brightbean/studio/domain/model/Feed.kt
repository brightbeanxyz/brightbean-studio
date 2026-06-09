package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Feed(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val url: String,
    val websiteUrl: String,
    val addedBy: UUID?,
    val createdAt: Instant,
)
