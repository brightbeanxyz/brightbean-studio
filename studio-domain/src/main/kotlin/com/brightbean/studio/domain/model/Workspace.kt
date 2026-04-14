package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Workspace(
    val id: UUID,
    val name: String,
    val description: String,
    val organizationId: UUID,
    val settings: WorkspaceSettings,
    val createdAt: Instant,
    val updatedAt: Instant,
)

data class WorkspaceSettings(
    val isPublic: Boolean = true,
    val allowMemberInvite: Boolean = false,
    val allowBoardCreation: Boolean = false,
    val allowCardCreation: Boolean = false,
)