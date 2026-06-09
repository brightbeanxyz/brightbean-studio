package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class ConnectionLink(
    val id: UUID,
    val workspaceId: UUID,
    val token: String,
    val createdBy: UUID?,
    val expiresAt: Instant,
    val revokedAt: Instant?,
    val createdAt: Instant,
) {
    val isExpired: Boolean get() = Instant.now().isAfter(expiresAt)
    val isRevoked: Boolean get() = revokedAt != null
    val isActive: Boolean get() = !isExpired && !isRevoked
}

data class ConnectionLinkUsage(
    val id: UUID,
    val connectionLinkId: UUID,
    val socialAccountId: UUID,
    val connectedAt: Instant,
)

data class OnboardingChecklist(
    val id: UUID,
    val userId: UUID,
    val workspaceId: UUID,
    val isDismissed: Boolean,
    val dismissedAt: Instant?,
)
