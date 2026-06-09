package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class MemberRole {
    OWNER,
    ADMIN,
    EDITOR,
    VIEWER,
}

data class Member(
    val id: UUID,
    val workspaceId: UUID,
    val userId: UUID,
    val role: MemberRole,
    val invitedBy: UUID? = null,
    val joinedAt: Instant,
)