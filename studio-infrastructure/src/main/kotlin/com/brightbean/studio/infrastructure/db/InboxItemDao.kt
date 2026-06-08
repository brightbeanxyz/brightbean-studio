package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterBeanMapper(InboxItemDto::class)
interface InboxItemDao {
    @SqlQuery("SELECT * FROM inbox_item WHERE id = :id")
    fun findById(id: UUID): InboxItemDto?

    @SqlQuery("SELECT * FROM inbox_item WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<InboxItemDto>

    @SqlQuery("SELECT * FROM inbox_item WHERE social_account_id = :socialAccountId")
    fun findBySocialAccountId(socialAccountId: UUID): List<InboxItemDto>

    @SqlUpdate("""
        INSERT INTO inbox_item (id, workspace_id, social_account_id, platform_type, platform_item_id, type, content, author_name, author_avatar_url, media_urls, sentiment, is_read, is_archived, platform_created_at, received_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.socialAccountId, :dto.platformType, :dto.platformItemId, :dto.type, :dto.content, :dto.authorName, :dto.authorAvatarUrl, :dto.mediaUrls, :dto.sentiment, :dto.isRead, :dto.isArchived, :dto.platformCreatedAt, :dto.receivedAt)
    """)
    fun insert(dto: InboxItemDto)

    @SqlUpdate("""
        UPDATE inbox_item SET
            content = :dto.content,
            author_name = :dto.authorName,
            author_avatar_url = :dto.authorAvatarUrl,
            media_urls = :dto.mediaUrls,
            sentiment = :dto.sentiment,
            is_read = :dto.isRead,
            is_archived = :dto.isArchived
        WHERE id = :dto.id
    """)
    fun update(dto: InboxItemDto)

    @SqlUpdate("DELETE FROM inbox_item WHERE id = :id")
    fun delete(id: UUID)
}

data class InboxItemDto(
    val id: UUID,
    val workspaceId: UUID,
    val socialAccountId: UUID,
    val platformType: String,
    val platformItemId: String,
    val type: String,
    val content: String,
    val authorName: String,
    val authorAvatarUrl: String?,
    val mediaUrls: String,
    val sentiment: String?,
    val isRead: Boolean,
    val isArchived: Boolean,
    val platformCreatedAt: Instant,
    val receivedAt: Instant,
)
