package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(IdeaGroupDto::class)
interface IdeaGroupDao {
    @SqlQuery("SELECT * FROM composer_idea_group WHERE id = :id")
    fun findById(id: UUID): IdeaGroupDto?

    @SqlQuery("SELECT * FROM composer_idea_group WHERE workspace_id = :workspaceId ORDER BY position")
    fun findByWorkspaceId(workspaceId: UUID): List<IdeaGroupDto>

    @SqlUpdate("""
        INSERT INTO composer_idea_group (id, workspace_id, name, position, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.position, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: IdeaGroupDto)

    @SqlUpdate("""
        UPDATE composer_idea_group SET
            name = :dto.name,
            position = :dto.position,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: IdeaGroupDto)

    @SqlUpdate("DELETE FROM composer_idea_group WHERE id = :id")
    fun delete(id: UUID)
}

data class IdeaGroupDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val position: Int,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
