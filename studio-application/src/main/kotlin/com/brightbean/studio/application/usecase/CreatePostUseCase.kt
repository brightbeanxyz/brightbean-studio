package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApprovalRequest
import com.brightbean.studio.domain.model.ApprovalStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class CreatePostUseCase(
    private val postRepository: PostRepository,
    private val approvalRequestRepository: ApprovalRequestRepository,
) {
    fun execute(
        workspaceId: UUID,
        authorId: UUID?,
        content: String,
        socialAccountIds: List<UUID>,
        scheduledAt: Instant?,
        requiresApproval: Boolean,
        categoryId: UUID? = null,
        tags: List<String> = emptyList(),
        mediaIds: List<UUID> = emptyList(),
    ): Post {
        val now = Instant.now()

        val post = Post(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = authorId,
            title = "",
            caption = content,
            firstComment = "",
            internalNotes = "",
            tags = tags,
            categoryId = categoryId,
            scheduledAt = scheduledAt,
            publishedAt = null,
            createdAt = now,
            updatedAt = now,
        )
        postRepository.save(post)

        if (requiresApproval) {
            val approvalRequest = ApprovalRequest(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                postId = post.id,
                requestedBy = authorId ?: throw IllegalArgumentException("authorId required for approval"),
                requestedAt = now,
                status = ApprovalStatus.PENDING,
                reviewedBy = null,
                reviewedAt = null,
                comment = null,
            )
            approvalRequestRepository.save(approvalRequest)
        }

        return post
    }
}
