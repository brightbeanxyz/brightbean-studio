package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Organization(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val logoUrl: String? = null,
    val website: String? = null,
    val createdAt: Instant,
)