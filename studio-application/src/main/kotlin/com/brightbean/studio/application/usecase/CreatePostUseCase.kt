package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApprovalRequest
import com.brightbean.studio.domain.model.ApprovalStatus
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.Tag
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
        authorId: UUID,
        content: String,
        platforms: List<PlatformType>,
        scheduledAt: Instant?,
        requiresApproval: Boolean,
        categoryId: UUID? = null,
        tags: List<Tag> = emptyList(),
        mediaIds: List<UUID> = emptyList(),
    ): Post {
        val now = Instant.now()
        val status = when {
            scheduledAt != null -> PostStatus.SCHEDULED
            requiresApproval -> PostStatus.PENDING_APPROVAL
            else -> PostStatus.DRAFT
        }

        val post = Post(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = authorId,
            content = content,
            platforms = platforms,
            categoryId = categoryId,
            tags = tags,
            status = status,
            scheduledAt = scheduledAt,
            publishedAt = null,
            mediaIds = mediaIds,
            createdAt = now,
            updatedAt = now,
        )
        postRepository.save(post)

        if (requiresApproval) {
            val approvalRequest = ApprovalRequest(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                postId = post.id,
                requestedBy = authorId,
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
