package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class InboxMessageType { COMMENT, MENTION, DM, REVIEW }
enum class InboxMessageStatus { UNREAD, OPEN, RESOLVED, ARCHIVED }

data class InboxMessage(
    val id: UUID,
    val workspaceId: UUID,
    val socialAccountId: UUID,
    val platformMessageId: String,
    val messageType: InboxMessageType,
    val senderName: String,
    val senderHandle: String,
    val senderAvatarUrl: String,
    val body: String,
    val sentiment: String,
    val sentimentSource: String,
    val status: InboxMessageStatus,
    val assignedTo: UUID?,
    val parentMessageId: UUID?,
    val relatedPostId: UUID?,
    val extra: String?,
    val receivedAt: Instant,
    val createdAt: Instant,
)

data class InboxReply(
    val id: UUID,
    val inboxMessageId: UUID,
    val authorId: UUID?,
    val body: String,
    val platformReplyId: String,
    val sentAt: Instant,
)

data class InternalNote(
    val id: UUID,
    val inboxMessageId: UUID,
    val authorId: UUID?,
    val body: String,
    val createdAt: Instant,
)

data class SavedReply(
    val id: UUID,
    val workspaceId: UUID,
    val title: String,
    val body: String,
    val createdBy: UUID?,
    val createdAt: Instant,
    val updatedAt: Instant,
)

data class InboxSLAConfig(
    val id: UUID,
    val workspaceId: UUID,
    val targetResponseMinutes: Int,
    val isActive: Boolean,
    val autoResolveOnReply: Boolean,
)
