package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class MemberRole {
    OWNER,
    ADMIN,
    MEMBER,
    GUEST,
}

data class Member(
    val id: UUID,
    val userId: UUID,
    val organizationId: UUID,
    val role: MemberRole,
    val joinedAt: Instant,
)