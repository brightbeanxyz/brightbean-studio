package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class OrgRole {
    OWNER,
    ADMIN,
    MEMBER,
}

data class OrgMembership(
    val id: UUID,
    val userId: UUID,
    val organizationId: UUID,
    val orgRole: OrgRole,
    val invitedAt: Instant,
    val acceptedAt: Instant? = null,
)
