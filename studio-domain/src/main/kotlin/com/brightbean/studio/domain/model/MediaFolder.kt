package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class MediaFolder(
    val id: UUID,
    val organizationId: UUID,
    val workspaceId: UUID?,
    val parentFolderId: UUID?,
    val name: String,
    val createdAt: Instant,
    val updatedAt: Instant,
)
