package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Workspace(
    val id: UUID,
    val organizationId: UUID,
    val name: String,
    val slug: String,
    val ownerId: UUID,
    val settings: WorkspaceSettings,
    val isArchived: Boolean = false,
    val createdAt: Instant,
    val updatedAt: Instant,
)

data class WorkspaceSettings(
    val defaultLanguage: String = "en",
    val timezone: String = "UTC",
    val postsPerPage: Int = 25,
)
