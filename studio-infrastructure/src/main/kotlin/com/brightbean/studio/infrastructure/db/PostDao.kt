package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterBeanMapper(PostDto::class)
interface PostDao {
    @SqlQuery("SELECT * FROM post WHERE id = :id")
    fun findById(id: UUID): PostDto?

    @SqlQuery("SELECT * FROM post WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<PostDto>

    @SqlQuery("SELECT * FROM post WHERE workspace_id = :workspaceId AND status = :status")
    fun findByStatus(workspaceId: UUID, status: String): List<PostDto>

    @SqlUpdate("""
        INSERT INTO post (id, workspace_id, author_id, content, platforms, category_id, tags, status, scheduled_at, published_at, media_ids, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.authorId, :dto.content, :dto.platforms, :dto.categoryId, :dto.tags, :dto.status, :dto.scheduledAt, :dto.publishedAt, :dto.mediaIds, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: PostDto)

    @SqlUpdate("""
        UPDATE post SET
            content = :dto.content,
            platforms = :dto.platforms,
            category_id = :dto.categoryId,
            tags = :dto.tags,
            status = :dto.status,
            scheduled_at = :dto.scheduledAt,
            published_at = :dto.publishedAt,
            media_ids = :dto.mediaIds,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PostDto)

    @SqlUpdate("DELETE FROM post WHERE id = :id")
    fun delete(id: UUID)
}

data class PostDto(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID,
    val content: String,
    val platforms: String,
    val categoryId: UUID?,
    val tags: String,
    val status: String,
    val scheduledAt: java.time.Instant?,
    val publishedAt: java.time.Instant?,
    val mediaIds: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
