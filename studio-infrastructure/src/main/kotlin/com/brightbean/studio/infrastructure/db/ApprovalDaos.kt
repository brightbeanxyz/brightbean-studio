package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterKotlinMapper(ApprovalActionDto::class)
interface ApprovalActionDao {
    @SqlQuery("SELECT * FROM approvals_approval_action WHERE post_id = :postId ORDER BY created_at")
    fun findByPostId(postId: UUID): List<ApprovalActionDto>

    @SqlUpdate("""
        INSERT INTO approvals_approval_action (id, post_id, platform_post_id, user_id, action, comment, created_at)
        VALUES (:dto.id, :dto.postId, :dto.platformPostId, :dto.userId, :dto.action, :dto.comment, :dto.createdAt)
    """)
    fun insert(dto: ApprovalActionDto)
}

data class ApprovalActionDto(
    val id: UUID,
    val postId: UUID,
    val platformPostId: UUID?,
    val userId: UUID?,
    val action: String,
    val comment: String,
    val createdAt: Instant,
)

@RegisterKotlinMapper(PostCommentDto::class)
interface PostCommentDao {
    @SqlQuery("SELECT * FROM approvals_post_comment WHERE post_id = :postId AND deleted_at IS NULL ORDER BY created_at")
    fun findByPostId(postId: UUID): List<PostCommentDto>

    @SqlUpdate("""
        INSERT INTO approvals_post_comment (id, post_id, author_id, parent_comment_id, body, visibility, created_at, updated_at, deleted_at)
        VALUES (:dto.id, :dto.postId, :dto.authorId, :dto.parentCommentId, :dto.body, :dto.visibility, :dto.createdAt, :dto.updatedAt, :dto.deletedAt)
    """)
    fun insert(dto: PostCommentDto)

    @SqlUpdate("""
        UPDATE approvals_post_comment SET body = :dto.body, visibility = :dto.visibility, updated_at = :dto.updatedAt, deleted_at = :dto.deletedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PostCommentDto)

    @SqlUpdate("DELETE FROM approvals_post_comment WHERE id = :id")
    fun delete(id: UUID)
}

data class PostCommentDto(
    val id: UUID,
    val postId: UUID,
    val authorId: UUID?,
    val parentCommentId: UUID?,
    val body: String,
    val visibility: String,
    val createdAt: Instant,
    val updatedAt: Instant,
    val deletedAt: Instant?,
)

@RegisterKotlinMapper(ApprovalReminderDto::class)
interface ApprovalReminderDao {
    @SqlQuery("SELECT * FROM approvals_approval_reminder WHERE post_id = :postId")
    fun findByPostId(postId: UUID): ApprovalReminderDto?

    @SqlUpdate("""
        INSERT INTO approvals_approval_reminder (id, post_id, stage, reminder_count, last_reminder_at, escalated)
        VALUES (:dto.id, :dto.postId, :dto.stage, :dto.reminderCount, :dto.lastReminderAt, :dto.escalated)
    """)
    fun insert(dto: ApprovalReminderDto)

    @SqlUpdate("""
        UPDATE approvals_approval_reminder SET stage = :dto.stage, reminder_count = :dto.reminderCount, last_reminder_at = :dto.lastReminderAt, escalated = :dto.escalated
        WHERE id = :dto.id
    """)
    fun update(dto: ApprovalReminderDto)
}

data class ApprovalReminderDto(
    val id: UUID,
    val postId: UUID,
    val stage: String,
    val reminderCount: Int,
    val lastReminderAt: Instant?,
    val escalated: Boolean,
)
