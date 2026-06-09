package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(TagDto::class)
interface TagDao {
    @SqlQuery("SELECT * FROM composer_tag WHERE id = :id")
    fun findById(id: UUID): TagDto?

    @SqlQuery("SELECT * FROM composer_tag WHERE workspace_id = :workspaceId ORDER BY name")
    fun findByWorkspaceId(workspaceId: UUID): List<TagDto>

    @SqlQuery("SELECT * FROM composer_tag WHERE workspace_id = :workspaceId AND name = :name")
    fun findByName(workspaceId: UUID, name: String): TagDto?

    @SqlUpdate("""
        INSERT INTO composer_tag (id, workspace_id, name, created_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.createdAt)
    """)
    fun insert(dto: TagDto)

    @SqlUpdate("DELETE FROM composer_tag WHERE id = :id")
    fun delete(id: UUID)
}

data class TagDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val createdAt: java.time.Instant,
)
