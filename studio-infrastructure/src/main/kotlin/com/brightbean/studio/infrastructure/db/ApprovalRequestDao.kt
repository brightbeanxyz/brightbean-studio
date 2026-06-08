package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterKotlinMapper(ApprovalRequestDto::class)
interface ApprovalRequestDao {
    @SqlQuery("SELECT * FROM approval_request WHERE id = :id")
    fun findById(id: UUID): ApprovalRequestDto?

    @SqlQuery("SELECT * FROM approval_request WHERE post_id = :postId")
    fun findByPostId(postId: UUID): List<ApprovalRequestDto>

    @SqlQuery("SELECT * FROM approval_request WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<ApprovalRequestDto>

    @SqlUpdate("""
        INSERT INTO approval_request (id, workspace_id, post_id, requested_by, requested_at, status, reviewed_by, reviewed_at, comment)
        VALUES (:dto.id, :dto.workspaceId, :dto.postId, :dto.requestedBy, :dto.requestedAt, :dto.status, :dto.reviewedBy, :dto.reviewedAt, :dto.comment)
    """)
    fun insert(dto: ApprovalRequestDto)

    @SqlUpdate("""
        UPDATE approval_request SET
            status = :dto.status,
            reviewed_by = :dto.reviewedBy,
            reviewed_at = :dto.reviewedAt,
            comment = :dto.comment
        WHERE id = :dto.id
    """)
    fun update(dto: ApprovalRequestDto)

    @SqlUpdate("DELETE FROM approval_request WHERE id = :id")
    fun delete(id: UUID)
}

data class ApprovalRequestDto(
    val id: UUID,
    val workspaceId: UUID,
    val postId: UUID,
    val requestedBy: UUID,
    val requestedAt: Instant,
    val status: String,
    val reviewedBy: UUID?,
    val reviewedAt: Instant?,
    val comment: String?,
)
