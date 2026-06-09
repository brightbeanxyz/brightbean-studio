package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApprovalAction
import com.brightbean.studio.domain.model.ApprovalActionType
import com.brightbean.studio.domain.model.PostComment
import com.brightbean.studio.domain.repository.ApprovalActionRepository
import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import com.brightbean.studio.domain.repository.PostCommentRepository
import com.brightbean.studio.domain.model.ApprovalRequest
import com.brightbean.studio.domain.model.ApprovalStatus
import java.time.Instant
import java.util.UUID

class ApprovalUseCases(
    private val approvalRequestRepository: ApprovalRequestRepository,
    private val approvalActionRepository: ApprovalActionRepository,
) {
    fun submitForReview(workspaceId: UUID, postId: UUID, requestedBy: UUID): ApprovalRequest {
        val request = ApprovalRequest(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            postId = postId,
            requestedBy = requestedBy,
            requestedAt = Instant.now(),
            status = ApprovalStatus.PENDING,
            reviewedBy = null,
            reviewedAt = null,
            comment = null,
        )
        approvalRequestRepository.save(request)
        approvalActionRepository.save(ApprovalAction(id = UUID.randomUUID(), postId = postId, platformPostId = null, userId = requestedBy, action = ApprovalActionType.SUBMITTED, comment = "", createdAt = Instant.now()))
        return request
    }

    fun approve(requestId: UUID, reviewerId: UUID, comment: String = ""): ApprovalRequest {
        val request = approvalRequestRepository.findById(requestId) ?: throw IllegalArgumentException("Approval request not found: $requestId")
        val updated = request.copy(status = ApprovalStatus.APPROVED, reviewedBy = reviewerId, reviewedAt = Instant.now(), comment = comment)
        approvalRequestRepository.update(updated)
        approvalActionRepository.save(ApprovalAction(id = UUID.randomUUID(), postId = request.postId, platformPostId = null, userId = reviewerId, action = ApprovalActionType.APPROVED, comment = comment, createdAt = Instant.now()))
        return updated
    }

    fun requestChanges(requestId: UUID, reviewerId: UUID, comment: String): ApprovalRequest {
        val request = approvalRequestRepository.findById(requestId) ?: throw IllegalArgumentException("Approval request not found: $requestId")
        val updated = request.copy(status = ApprovalStatus.CHANGES_REQUESTED, reviewedBy = reviewerId, reviewedAt = Instant.now(), comment = comment)
        approvalRequestRepository.update(updated)
        approvalActionRepository.save(ApprovalAction(id = UUID.randomUUID(), postId = request.postId, platformPostId = null, userId = reviewerId, action = ApprovalActionType.CHANGES_REQUESTED, comment = comment, createdAt = Instant.now()))
        return updated
    }

    fun reject(requestId: UUID, reviewerId: UUID, comment: String): ApprovalRequest {
        val request = approvalRequestRepository.findById(requestId) ?: throw IllegalArgumentException("Approval request not found: $requestId")
        val updated = request.copy(status = ApprovalStatus.REJECTED, reviewedBy = reviewerId, reviewedAt = Instant.now(), comment = comment)
        approvalRequestRepository.update(updated)
        approvalActionRepository.save(ApprovalAction(id = UUID.randomUUID(), postId = request.postId, platformPostId = null, userId = reviewerId, action = ApprovalActionType.REJECTED, comment = comment, createdAt = Instant.now()))
        return updated
    }

    fun resubmit(requestId: UUID, userId: UUID, comment: String = ""): ApprovalRequest {
        val request = approvalRequestRepository.findById(requestId) ?: throw IllegalArgumentException("Approval request not found: $requestId")
        val updated = request.copy(status = ApprovalStatus.PENDING, reviewedBy = null, reviewedAt = null, comment = null)
        approvalRequestRepository.update(updated)
        approvalActionRepository.save(ApprovalAction(id = UUID.randomUUID(), postId = request.postId, platformPostId = null, userId = userId, action = ApprovalActionType.RESUBMITTED, comment = comment, createdAt = Instant.now()))
        return updated
    }

    fun bulkApprove(requestIds: List<UUID>, reviewerId: UUID) = requestIds.map { approve(it, reviewerId) }
    fun bulkReject(requestIds: List<UUID>, reviewerId: UUID, comment: String) = requestIds.map { reject(it, reviewerId, comment) }
}

class CommentUseCases(
    private val postCommentRepository: PostCommentRepository,
) {
    fun createComment(postId: UUID, authorId: UUID?, body: String, visibility: String = "internal", parentCommentId: UUID? = null): PostComment {
        val now = Instant.now()
        return postCommentRepository.save(PostComment(id = UUID.randomUUID(), postId = postId, authorId = authorId, parentCommentId = parentCommentId, body = body, visibility = visibility, createdAt = now, updatedAt = now, deletedAt = null))
    }

    fun updateComment(commentId: UUID, body: String): PostComment {
        val comment = postCommentRepository.findByPostId(commentId).firstOrNull { it.id == commentId } ?: throw IllegalArgumentException("Comment not found: $commentId")
        return postCommentRepository.update(comment.copy(body = body, updatedAt = Instant.now()))
    }

    fun deleteComment(commentId: UUID) {
        val comments = postCommentRepository.findByPostId(commentId)
        val comment = comments.firstOrNull { it.id == commentId } ?: return
        postCommentRepository.update(comment.copy(deletedAt = Instant.now()))
    }

    fun getCommentsForPost(postId: UUID): List<PostComment> = postCommentRepository.findByPostId(postId)
}
