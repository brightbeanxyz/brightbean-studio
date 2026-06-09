package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostMedia
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostMediaRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class CreatePostUseCase(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
    private val postMediaRepository: PostMediaRepository,
) {
    data class Request(
        val workspaceId: UUID,
        val authorId: UUID?,
        val title: String,
        val caption: String,
        val firstComment: String,
        val internalNotes: String,
        val tags: List<String>,
        val categoryId: UUID?,
        val socialAccountIds: List<UUID>,
        val mediaAssetIds: List<UUID>,
        val scheduledAt: Instant?,
    )

    data class Result(
        val post: Post,
        val platformPosts: List<PlatformPost>,
        val postMedia: List<PostMedia>,
    )

    fun execute(request: Request): Result {
        val now = Instant.now()

        val post = Post(
            id = UUID.randomUUID(),
            workspaceId = request.workspaceId,
            authorId = request.authorId,
            title = request.title,
            caption = request.caption,
            firstComment = request.firstComment,
            internalNotes = request.internalNotes,
            tags = request.tags,
            categoryId = request.categoryId,
            scheduledAt = request.scheduledAt,
            publishedAt = null,
            createdAt = now,
            updatedAt = now,
        )
        postRepository.save(post)

        val platformPosts = request.socialAccountIds.map { accountId ->
            val pp = PlatformPost(
                id = UUID.randomUUID(),
                postId = post.id,
                socialAccountId = accountId,
                platformTitle = null,
                platformCaption = null,
                platformFirstComment = null,
                platformMedia = null,
                platformExtra = null,
                status = PlatformPostStatus.DRAFT,
                platformPostId = "",
                publishError = "",
                publishedAt = null,
                scheduledAt = request.scheduledAt,
                retryCount = 0,
                nextRetryAt = null,
                createdAt = now,
                updatedAt = now,
            )
            platformPostRepository.save(pp)
            pp
        }

        val postMedia = request.mediaAssetIds.mapIndexed { index, assetId ->
            val pm = PostMedia(
                id = UUID.randomUUID(),
                postId = post.id,
                mediaAssetId = assetId,
                position = index,
                altText = "",
                platformOverrides = null,
            )
            postMediaRepository.save(pm)
            pm
        }

        return Result(post, platformPosts, postMedia)
    }
}
