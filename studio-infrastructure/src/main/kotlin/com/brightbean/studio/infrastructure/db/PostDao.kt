package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(PostDto::class)
interface PostDao {
    @SqlQuery("SELECT * FROM composer_post WHERE id = :id")
    fun findById(id: UUID): PostDto?

    @SqlQuery("SELECT * FROM composer_post WHERE workspace_id = :workspaceId ORDER BY created_at DESC")
    fun findByWorkspaceId(workspaceId: UUID): List<PostDto>

    @SqlQuery("SELECT * FROM composer_post WHERE author_id = :authorId ORDER BY created_at DESC")
    fun findByAuthorId(authorId: UUID): List<PostDto>

    @SqlUpdate("""
        INSERT INTO composer_post (id, workspace_id, author_id, title, caption, first_comment, internal_notes, tags, category_id, scheduled_at, published_at, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.authorId, :dto.title, :dto.caption, :dto.firstComment, :dto.internalNotes, :dto.tags, :dto.categoryId, :dto.scheduledAt, :dto.publishedAt, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: PostDto)

    @SqlUpdate("""
        UPDATE composer_post SET
            title = :dto.title,
            caption = :dto.caption,
            first_comment = :dto.firstComment,
            internal_notes = :dto.internalNotes,
            tags = :dto.tags,
            category_id = :dto.categoryId,
            scheduled_at = :dto.scheduledAt,
            published_at = :dto.publishedAt,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PostDto)

    @SqlUpdate("DELETE FROM composer_post WHERE id = :id")
    fun delete(id: UUID)
}

data class PostDto(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID?,
    val title: String,
    val caption: String,
    val firstComment: String,
    val internalNotes: String,
    val tags: String,
    val categoryId: UUID?,
    val scheduledAt: java.time.Instant?,
    val publishedAt: java.time.Instant?,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
