package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(ContentCategoryDto::class)
interface ContentCategoryDao {
    @SqlQuery("SELECT * FROM composer_content_category WHERE id = :id")
    fun findById(id: UUID): ContentCategoryDto?

    @SqlQuery("SELECT * FROM composer_content_category WHERE workspace_id = :workspaceId ORDER BY position")
    fun findByWorkspaceId(workspaceId: UUID): List<ContentCategoryDto>

    @SqlUpdate("""
        INSERT INTO composer_content_category (id, workspace_id, name, color, position, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.color, :dto.position, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: ContentCategoryDto)

    @SqlUpdate("""
        UPDATE composer_content_category SET
            name = :dto.name,
            color = :dto.color,
            position = :dto.position,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: ContentCategoryDto)

    @SqlUpdate("DELETE FROM composer_content_category WHERE id = :id")
    fun delete(id: UUID)
}

data class ContentCategoryDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val color: String,
    val position: Int,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
