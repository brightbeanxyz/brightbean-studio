package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class ApprovalRequest(
    val id: UUID,
    val workspaceId: UUID,
    val postId: UUID,
    val requestedBy: UUID,
    val requestedAt: Instant,
    val status: ApprovalStatus,
    val reviewedBy: UUID?,
    val reviewedAt: Instant?,
    val comment: String?,
)
