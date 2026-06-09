package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(PostTemplateDto::class)
interface PostTemplateDao {
    @SqlQuery("SELECT * FROM composer_post_template WHERE id = :id")
    fun findById(id: UUID): PostTemplateDto?

    @SqlQuery("SELECT * FROM composer_post_template WHERE workspace_id = :workspaceId ORDER BY name")
    fun findByWorkspaceId(workspaceId: UUID): List<PostTemplateDto>

    @SqlUpdate("""
        INSERT INTO composer_post_template (id, workspace_id, name, description, template_data, created_by, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.description, :dto.templateData, :dto.createdBy, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: PostTemplateDto)

    @SqlUpdate("""
        UPDATE composer_post_template SET
            name = :dto.name,
            description = :dto.description,
            template_data = :dto.templateData,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PostTemplateDto)

    @SqlUpdate("DELETE FROM composer_post_template WHERE id = :id")
    fun delete(id: UUID)
}

data class PostTemplateDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val description: String,
    val templateData: String,
    val createdBy: UUID?,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
