package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class InvitationStatus {
    PENDING,
    ACCEPTED,
    EXPIRED,
    REVOKED,
}

data class Invitation(
    val id: UUID,
    val organizationId: UUID,
    val email: String,
    val orgRole: OrgRole,
    val workspaceAssignments: String,
    val invitedBy: UUID?,
    val token: String,
    val expiresAt: Instant,
    val acceptedAt: Instant? = null,
    val status: InvitationStatus,
    val createdAt: Instant,
)
