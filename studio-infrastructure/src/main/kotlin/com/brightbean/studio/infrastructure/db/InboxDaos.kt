package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterKotlinMapper(InboxMessageDto::class)
interface InboxMessageDao {
    @SqlQuery("SELECT * FROM inbox_message WHERE id = :id")
    fun findById(id: UUID): InboxMessageDto?

    @SqlQuery("SELECT * FROM inbox_message WHERE workspace_id = :workspaceId ORDER BY received_at DESC")
    fun findByWorkspaceId(workspaceId: UUID): List<InboxMessageDto>

    @SqlQuery("SELECT * FROM inbox_message WHERE workspace_id = :workspaceId AND status = :status ORDER BY received_at DESC")
    fun findByStatus(workspaceId: UUID, status: String): List<InboxMessageDto>

    @SqlQuery("SELECT * FROM inbox_message WHERE workspace_id = :workspaceId AND assigned_to = :userId ORDER BY received_at DESC")
    fun findByAssignedTo(workspaceId: UUID, userId: UUID): List<InboxMessageDto>

    @SqlQuery("SELECT * FROM inbox_message WHERE social_account_id = :socialAccountId AND platform_message_id = :platformMessageId")
    fun findByPlatformMessageId(socialAccountId: UUID, platformMessageId: String): InboxMessageDto?

    @SqlUpdate("""
        INSERT INTO inbox_message (id, workspace_id, social_account_id, platform_message_id, message_type, sender_name, sender_handle, sender_avatar_url, body, sentiment, sentiment_source, status, assigned_to, parent_message_id, related_post_id, extra, received_at, created_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.socialAccountId, :dto.platformMessageId, :dto.messageType, :dto.senderName, :dto.senderHandle, :dto.senderAvatarUrl, :dto.body, :dto.sentiment, :dto.sentimentSource, :dto.status, :dto.assignedTo, :dto.parentMessageId, :dto.relatedPostId, :dto.extra, :dto.receivedAt, :dto.createdAt)
    """)
    fun insert(dto: InboxMessageDto)

    @SqlUpdate("""
        UPDATE inbox_message SET
            sender_name = :dto.senderName,
            sender_handle = :dto.senderHandle,
            sender_avatar_url = :dto.senderAvatarUrl,
            body = :dto.body,
            sentiment = :dto.sentiment,
            sentiment_source = :dto.sentimentSource,
            status = :dto.status,
            assigned_to = :dto.assignedTo,
            parent_message_id = :dto.parentMessageId,
            related_post_id = :dto.relatedPostId,
            extra = :dto.extra
        WHERE id = :dto.id
    """)
    fun update(dto: InboxMessageDto)

    @SqlUpdate("DELETE FROM inbox_message WHERE id = :id")
    fun delete(id: UUID)
}

data class InboxMessageDto(
    val id: UUID,
    val workspaceId: UUID,
    val socialAccountId: UUID,
    val platformMessageId: String,
    val messageType: String,
    val senderName: String,
    val senderHandle: String,
    val senderAvatarUrl: String,
    val body: String,
    val sentiment: String,
    val sentimentSource: String,
    val status: String,
    val assignedTo: UUID?,
    val parentMessageId: UUID?,
    val relatedPostId: UUID?,
    val extra: String?,
    val receivedAt: Instant,
    val createdAt: Instant,
)

@RegisterKotlinMapper(InboxReplyDto::class)
interface InboxReplyDao {
    @SqlQuery("SELECT * FROM inbox_reply WHERE inbox_message_id = :messageId ORDER BY sent_at")
    fun findByMessageId(messageId: UUID): List<InboxReplyDto>

    @SqlUpdate("""
        INSERT INTO inbox_reply (id, inbox_message_id, author_id, body, platform_reply_id, sent_at)
        VALUES (:dto.id, :dto.inboxMessageId, :dto.authorId, :dto.body, :dto.platformReplyId, :dto.sentAt)
    """)
    fun insert(dto: InboxReplyDto)

    @SqlUpdate("DELETE FROM inbox_reply WHERE id = :id")
    fun delete(id: UUID)
}

data class InboxReplyDto(
    val id: UUID,
    val inboxMessageId: UUID,
    val authorId: UUID?,
    val body: String,
    val platformReplyId: String,
    val sentAt: Instant,
)

@RegisterKotlinMapper(InternalNoteDto::class)
interface InternalNoteDao {
    @SqlQuery("SELECT * FROM inbox_internal_note WHERE inbox_message_id = :messageId ORDER BY created_at")
    fun findByMessageId(messageId: UUID): List<InternalNoteDto>

    @SqlUpdate("""
        INSERT INTO inbox_internal_note (id, inbox_message_id, author_id, body, created_at)
        VALUES (:dto.id, :dto.inboxMessageId, :dto.authorId, :dto.body, :dto.createdAt)
    """)
    fun insert(dto: InternalNoteDto)

    @SqlUpdate("DELETE FROM inbox_internal_note WHERE id = :id")
    fun delete(id: UUID)
}

data class InternalNoteDto(
    val id: UUID,
    val inboxMessageId: UUID,
    val authorId: UUID?,
    val body: String,
    val createdAt: Instant,
)

@RegisterKotlinMapper(SavedReplyDto::class)
interface SavedReplyDao {
    @SqlQuery("SELECT * FROM inbox_saved_reply WHERE workspace_id = :workspaceId ORDER BY title")
    fun findByWorkspaceId(workspaceId: UUID): List<SavedReplyDto>

    @SqlUpdate("""
        INSERT INTO inbox_saved_reply (id, workspace_id, title, body, created_by, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.title, :dto.body, :dto.createdBy, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: SavedReplyDto)

    @SqlUpdate("""
        UPDATE inbox_saved_reply SET title = :dto.title, body = :dto.body, updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: SavedReplyDto)

    @SqlUpdate("DELETE FROM inbox_saved_reply WHERE id = :id")
    fun delete(id: UUID)
}

data class SavedReplyDto(
    val id: UUID,
    val workspaceId: UUID,
    val title: String,
    val body: String,
    val createdBy: UUID?,
    val createdAt: Instant,
    val updatedAt: Instant,
)

@RegisterKotlinMapper(InboxSLAConfigDto::class)
interface InboxSLAConfigDao {
    @SqlQuery("SELECT * FROM inbox_sla_config WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): InboxSLAConfigDto?

    @SqlUpdate("""
        INSERT INTO inbox_sla_config (id, workspace_id, target_response_minutes, is_active, auto_resolve_on_reply)
        VALUES (:dto.id, :dto.workspaceId, :dto.targetResponseMinutes, :dto.isActive, :dto.autoResolveOnReply)
    """)
    fun insert(dto: InboxSLAConfigDto)

    @SqlUpdate("""
        UPDATE inbox_sla_config SET target_response_minutes = :dto.targetResponseMinutes, is_active = :dto.isActive, auto_resolve_on_reply = :dto.autoResolveOnReply
        WHERE id = :dto.id
    """)
    fun update(dto: InboxSLAConfigDto)
}

data class InboxSLAConfigDto(
    val id: UUID,
    val workspaceId: UUID,
    val targetResponseMinutes: Int,
    val isActive: Boolean,
    val autoResolveOnReply: Boolean,
)
