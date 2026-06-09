package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(QueueDto::class)
interface QueueDao {
    @SqlQuery("SELECT * FROM calendar_queue WHERE id = :id")
    fun findById(id: UUID): QueueDto?

    @SqlQuery("SELECT * FROM calendar_queue WHERE workspace_id = :workspaceId ORDER BY name")
    fun findByWorkspaceId(workspaceId: UUID): List<QueueDto>

    @SqlUpdate("""
        INSERT INTO calendar_queue (id, workspace_id, name, category_id, social_account_id, is_active, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.categoryId, :dto.socialAccountId, :dto.isActive, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: QueueDto)

    @SqlUpdate("""
        UPDATE calendar_queue SET
            name = :dto.name,
            category_id = :dto.categoryId,
            social_account_id = :dto.socialAccountId,
            is_active = :dto.isActive,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: QueueDto)

    @SqlUpdate("DELETE FROM calendar_queue WHERE id = :id")
    fun delete(id: UUID)
}

data class QueueDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val categoryId: UUID?,
    val socialAccountId: UUID,
    val isActive: Boolean,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
