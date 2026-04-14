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

    @SqlUpdate("INSERT INTO workspace (id, name, slug, owner_id, settings, created_at, updated_at) VALUES (:dto.id, :dto.name, :dto.slug, :dto.ownerId, :dto.settings, :dto.createdAt, :dto.updatedAt)")
    fun insert(dto: WorkspaceDto)

    @SqlUpdate("DELETE FROM workspace WHERE id = :id")
    fun delete(id: UUID)
}

data class WorkspaceDto(
    val id: UUID,
    val name: String,
    val slug: String,
    val ownerId: UUID,
    val settings: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
