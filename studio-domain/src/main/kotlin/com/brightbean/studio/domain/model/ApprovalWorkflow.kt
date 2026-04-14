package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class ApprovalWorkflow(
    val id: UUID,
    val workspaceId: UUID,
    val postId: UUID,
    val requestedBy: UUID,
    val requestedAt: Instant,
    val status: ApprovalStatus,
    val reviewedBy: UUID?,
    val reviewedAt: Instant?,
    val comment: String?,
) {
    fun approve(reviewerId: UUID, reviewedAt: Instant, comment: String? = null): ApprovalWorkflow {
        return copy(
            status = ApprovalStatus.APPROVED,
            reviewedBy = reviewerId,
            reviewedAt = reviewedAt,
            comment = comment
        )
    }

    fun reject(reviewerId: UUID, reviewedAt: Instant, comment: String?): ApprovalWorkflow {
        return copy(
            status = ApprovalStatus.REJECTED,
            reviewedBy = reviewerId,
            reviewedAt = reviewedAt,
            comment = comment
        )
    }

    fun requestChanges(reviewerId: UUID, reviewedAt: Instant, comment: String?): ApprovalWorkflow {
        return copy(
            status = ApprovalStatus.CHANGES_REQUESTED,
            reviewedBy = reviewerId,
            reviewedAt = reviewedAt,
            comment = comment
        )
    }

    fun isPending(): Boolean = status == ApprovalStatus.PENDING
    fun isApproved(): Boolean = status == ApprovalStatus.APPROVED
    fun isRejected(): Boolean = status == ApprovalStatus.REJECTED
    fun isChangesRequested(): Boolean = status == ApprovalStatus.CHANGES_REQUESTED
}
