package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class ApprovalActionType { SUBMITTED, APPROVED, CHANGES_REQUESTED, REJECTED, RESUBMITTED }

data class ApprovalAction(
    val id: UUID,
    val postId: UUID,
    val platformPostId: UUID?,
    val userId: UUID?,
    val action: ApprovalActionType,
    val comment: String,
    val createdAt: Instant,
)

data class PostComment(
    val id: UUID,
    val postId: UUID,
    val authorId: UUID?,
    val parentCommentId: UUID?,
    val body: String,
    val visibility: String,
    val createdAt: Instant,
    val updatedAt: Instant,
    val deletedAt: Instant?,
)

data class ApprovalReminder(
    val id: UUID,
    val postId: UUID,
    val stage: String,
    val reminderCount: Int,
    val lastReminderAt: Instant?,
    val escalated: Boolean,
)
