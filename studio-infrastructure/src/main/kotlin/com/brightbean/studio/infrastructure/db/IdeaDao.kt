package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(IdeaDto::class)
interface IdeaDao {
    @SqlQuery("SELECT * FROM composer_idea WHERE id = :id")
    fun findById(id: UUID): IdeaDto?

    @SqlQuery("SELECT * FROM composer_idea WHERE workspace_id = :workspaceId ORDER BY position")
    fun findByWorkspaceId(workspaceId: UUID): List<IdeaDto>

    @SqlQuery("SELECT * FROM composer_idea WHERE group_id = :groupId ORDER BY position")
    fun findByGroupId(groupId: UUID): List<IdeaDto>

    @SqlQuery("SELECT * FROM composer_idea WHERE author_id = :authorId ORDER BY created_at DESC")
    fun findByAuthorId(authorId: UUID): List<IdeaDto>

    @SqlUpdate("""
        INSERT INTO composer_idea (id, workspace_id, author_id, title, description, tags, media_asset_id, status, group_id, position, post_id, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.authorId, :dto.title, :dto.description, :dto.tags, :dto.mediaAssetId, :dto.status, :dto.groupId, :dto.position, :dto.postId, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: IdeaDto)

    @SqlUpdate("""
        UPDATE composer_idea SET
            title = :dto.title,
            description = :dto.description,
            tags = :dto.tags,
            media_asset_id = :dto.mediaAssetId,
            status = :dto.status,
            group_id = :dto.groupId,
            position = :dto.position,
            post_id = :dto.postId,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: IdeaDto)

    @SqlUpdate("DELETE FROM composer_idea WHERE id = :id")
    fun delete(id: UUID)
}

data class IdeaDto(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID?,
    val title: String,
    val description: String,
    val tags: String,
    val mediaAssetId: UUID?,
    val status: String,
    val groupId: UUID?,
    val position: Int,
    val postId: UUID?,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
