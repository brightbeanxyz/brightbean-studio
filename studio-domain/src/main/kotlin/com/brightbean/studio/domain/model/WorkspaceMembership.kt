package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class WorkspaceRole {
    OWNER,
    MANAGER,
    EDITOR,
    CONTRIBUTOR,
    CLIENT,
    VIEWER,
}

data class WorkspaceMembership(
    val id: UUID,
    val userId: UUID,
    val workspaceId: UUID,
    val workspaceRole: WorkspaceRole,
    val customRoleId: UUID? = null,
    val addedAt: Instant,
)
