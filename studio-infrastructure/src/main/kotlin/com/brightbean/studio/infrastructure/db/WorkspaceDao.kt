package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(WorkspaceDto::class)
interface WorkspaceDao {
    @SqlQuery("SELECT * FROM workspace WHERE id = :id")
    fun findById(id: UUID): WorkspaceDto?

    @SqlQuery("SELECT * FROM workspace WHERE slug = :slug")
    fun findBySlug(slug: String): WorkspaceDto?

    @SqlQuery("SELECT * FROM workspace WHERE organization_id = :organizationId")
    fun findByOrganizationId(organizationId: UUID): List<WorkspaceDto>

    @SqlUpdate("""
        INSERT INTO workspace (id, organization_id, name, slug, owner_id, settings, is_archived, created_at, updated_at)
        VALUES (:dto.id, :dto.organizationId, :dto.name, :dto.slug, :dto.ownerId, :dto.settings, :dto.isArchived, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: WorkspaceDto)

    @SqlUpdate("""
        UPDATE workspace SET
            name = :dto.name,
            slug = :dto.slug,
            settings = :dto.settings,
            is_archived = :dto.isArchived,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: WorkspaceDto)

    @SqlUpdate("DELETE FROM workspace WHERE id = :id")
    fun delete(id: UUID)
}

data class WorkspaceDto(
    val id: UUID,
    val organizationId: UUID,
    val name: String,
    val slug: String,
    val ownerId: UUID,
    val settings: String,
    val isArchived: Boolean,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
