package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class MagicLinkToken(
    val id: UUID,
    val userId: UUID,
    val workspaceId: UUID,
    val token: String,
    val createdAt: Instant,
    val expiresAt: Instant,
    val lastUsedAt: Instant?,
    val isConsumed: Boolean,
)
