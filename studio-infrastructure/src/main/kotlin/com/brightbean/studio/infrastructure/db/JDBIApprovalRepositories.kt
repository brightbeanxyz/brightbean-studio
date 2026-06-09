package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.ApprovalAction
import com.brightbean.studio.domain.model.ApprovalActionType
import com.brightbean.studio.domain.model.ApprovalReminder
import com.brightbean.studio.domain.model.PostComment
import com.brightbean.studio.domain.repository.ApprovalActionRepository
import com.brightbean.studio.domain.repository.ApprovalReminderRepository
import com.brightbean.studio.domain.repository.PostCommentRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIApprovalActionRepository(jdbi: Jdbi) : ApprovalActionRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: ApprovalActionDao by lazy { jdbi.onDemand(ApprovalActionDao::class.java) }

    override fun findByPostId(postId: UUID): List<ApprovalAction> = dao.findByPostId(postId).map { it.toDomain() }
    override fun save(action: ApprovalAction): ApprovalAction { dao.insert(action.toDto()); return action }

    private fun ApprovalAction.toDto() = ApprovalActionDto(id, postId, platformPostId, userId, action.name, comment, createdAt)
    private fun ApprovalActionDto.toDomain() = ApprovalAction(id, postId, platformPostId, userId, ApprovalActionType.valueOf(action), comment, createdAt)
}

class JDBIPostCommentRepository(jdbi: Jdbi) : PostCommentRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: PostCommentDao by lazy { jdbi.onDemand(PostCommentDao::class.java) }

    override fun findByPostId(postId: UUID): List<PostComment> = dao.findByPostId(postId).map { it.toDomain() }
    override fun save(comment: PostComment): PostComment { dao.insert(comment.toDto()); return comment }
    override fun update(comment: PostComment): PostComment { dao.update(comment.toDto()); return comment }
    override fun delete(id: UUID) = dao.delete(id)

    private fun PostComment.toDto() = PostCommentDto(id, postId, authorId, parentCommentId, body, visibility, createdAt, updatedAt, deletedAt)
    private fun PostCommentDto.toDomain() = PostComment(id, postId, authorId, parentCommentId, body, visibility, createdAt, updatedAt, deletedAt)
}

class JDBIApprovalReminderRepository(jdbi: Jdbi) : ApprovalReminderRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: ApprovalReminderDao by lazy { jdbi.onDemand(ApprovalReminderDao::class.java) }

    override fun findByPostId(postId: UUID): ApprovalReminder? = dao.findByPostId(postId)?.toDomain()
    override fun save(reminder: ApprovalReminder): ApprovalReminder { dao.insert(reminder.toDto()); return reminder }
    override fun update(reminder: ApprovalReminder): ApprovalReminder { dao.update(reminder.toDto()); return reminder }

    private fun ApprovalReminder.toDto() = ApprovalReminderDto(id, postId, stage, reminderCount, lastReminderAt, escalated)
    private fun ApprovalReminderDto.toDomain() = ApprovalReminder(id, postId, stage, reminderCount, lastReminderAt, escalated)
}
