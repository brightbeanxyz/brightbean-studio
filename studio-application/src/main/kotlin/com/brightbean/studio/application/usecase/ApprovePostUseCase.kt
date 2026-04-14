package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApprovalStatus
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class ApprovePostUseCase(
    private val approvalRequestRepository: ApprovalRequestRepository,
    private val postRepository: PostRepository,
) {
    fun execute(
        approvalRequestId: UUID,
        reviewerId: UUID,
        approved: Boolean,
        comment: String? = null,
    ) {
        val approvalRequest = approvalRequestRepository.findById(approvalRequestId)
            ?: throw IllegalArgumentException("Approval request not found: $approvalRequestId")

        if (!approvalRequest.isPending()) {
            throw IllegalArgumentException("Approval request is not pending: ${approvalRequest.status}")
        }

        val now = Instant.now()
        val updatedRequest = approvalRequest.copy(
            status = if (approved) ApprovalStatus.APPROVED else ApprovalStatus.REJECTED,
            reviewedBy = reviewerId,
            reviewedAt = now,
            comment = comment,
        )
        approvalRequestRepository.update(updatedRequest)

        if (approved) {
            val post = postRepository.findById(approvalRequest.postId)
                ?: throw IllegalStateException("Post not found: ${approvalRequest.postId}")
            val updatedPost = post.copy(
                status = PostStatus.DRAFT,
                updatedAt = now,
            )
            postRepository.update(updatedPost)
        }
    }

    private fun com.brightbean.studio.domain.model.ApprovalRequest.isPending(): Boolean =
        status == ApprovalStatus.PENDING
}
