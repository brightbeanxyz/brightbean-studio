package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterKotlinMapper(PublishingQueueDto::class)
interface PublishingQueueDao {
    @SqlQuery("SELECT * FROM publishing_queue WHERE id = :id")
    fun findById(id: UUID): PublishingQueueDto?

    @SqlQuery("SELECT * FROM publishing_queue WHERE post_id = :postId")
    fun findByPostId(postId: UUID): List<PublishingQueueDto>

    @SqlQuery("SELECT * FROM publishing_queue WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<PublishingQueueDto>

    @SqlQuery("SELECT * FROM publishing_queue WHERE status = 'PENDING'")
    fun findPending(): List<PublishingQueueDto>

    @SqlUpdate("""
        INSERT INTO publishing_queue (id, workspace_id, post_id, scheduled_for, attempts, last_attempt_at, status, error_message)
        VALUES (:dto.id, :dto.workspaceId, :dto.postId, :dto.scheduledFor, :dto.attempts, :dto.lastAttemptAt, :dto.status, :dto.errorMessage)
    """)
    fun insert(dto: PublishingQueueDto)

    @SqlUpdate("""
        UPDATE publishing_queue SET
            scheduled_for = :dto.scheduledFor,
            attempts = :dto.attempts,
            last_attempt_at = :dto.lastAttemptAt,
            status = :dto.status,
            error_message = :dto.errorMessage
        WHERE id = :dto.id
    """)
    fun update(dto: PublishingQueueDto)

    @SqlUpdate("DELETE FROM publishing_queue WHERE id = :id")
    fun delete(id: UUID)
}

data class PublishingQueueDto(
    val id: UUID,
    val workspaceId: UUID,
    val postId: UUID,
    val scheduledFor: Instant,
    val attempts: Int,
    val lastAttemptAt: Instant?,
    val status: String,
    val errorMessage: String?,
)
