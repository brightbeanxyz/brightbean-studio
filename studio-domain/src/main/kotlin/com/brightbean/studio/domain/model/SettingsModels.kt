package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class OrgSetting(
    val id: UUID,
    val organizationId: UUID,
    val key: String,
    val value: String,
    val updatedAt: Instant,
)

data class WorkspaceSetting(
    val id: UUID,
    val workspaceId: UUID,
    val key: String,
    val value: String?,
    val updatedAt: Instant,
)
