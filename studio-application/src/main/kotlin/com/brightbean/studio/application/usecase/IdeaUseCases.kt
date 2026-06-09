package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Idea
import com.brightbean.studio.domain.model.IdeaMedia
import com.brightbean.studio.domain.model.IdeaStatus
import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostMedia
import com.brightbean.studio.domain.repository.IdeaMediaRepository
import com.brightbean.studio.domain.repository.IdeaRepository
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostMediaRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import java.time.Instant
import java.util.UUID

class IdeaUseCases(
    private val ideaRepository: IdeaRepository,
    private val ideaMediaRepository: IdeaMediaRepository,
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
    private val postMediaRepository: PostMediaRepository,
    private val socialAccountRepository: SocialAccountRepository,
) {

    fun listByWorkspace(workspaceId: UUID): List<Idea> =
        ideaRepository.findByWorkspaceId(workspaceId)

    fun listByGroup(groupId: UUID): List<Idea> =
        ideaRepository.findByGroupId(groupId)

    fun create(
        workspaceId: UUID,
        authorId: UUID?,
        title: String,
        description: String,
        tags: List<String>,
        mediaAssetIds: List<UUID>,
        groupId: UUID?,
    ): Idea {
        val now = Instant.now()
        val idea = Idea(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = authorId,
            title = title,
            description = description,
            tags = tags,
            mediaAssetId = mediaAssetIds.firstOrNull(),
            status = if (groupId != null) IdeaStatus.TODO else IdeaStatus.UNASSIGNED,
            groupId = groupId,
            position = 0,
            postId = null,
            createdAt = now,
            updatedAt = now,
        )
        ideaRepository.save(idea)

        mediaAssetIds.forEachIndexed { index, assetId ->
            ideaMediaRepository.save(IdeaMedia(
                id = UUID.randomUUID(),
                ideaId = idea.id,
                mediaAssetId = assetId,
                position = index,
                createdAt = now,
                updatedAt = now,
            ))
        }

        return idea
    }

    fun update(
        ideaId: UUID,
        title: String?,
        description: String?,
        tags: List<String>?,
        groupId: UUID?,
        mediaAssetIds: List<UUID>?,
    ): Idea {
        val idea = ideaRepository.findById(ideaId)
            ?: throw IllegalArgumentException("Idea not found: $ideaId")
        val updated = idea.copy(
            title = title ?: idea.title,
            description = description ?: idea.description,
            tags = tags ?: idea.tags,
            groupId = groupId ?: idea.groupId,
            updatedAt = Instant.now(),
        )
        ideaRepository.update(updated)

        if (mediaAssetIds != null) {
            ideaMediaRepository.deleteByIdeaId(ideaId)
            val now = Instant.now()
            mediaAssetIds.forEachIndexed { index, assetId ->
                ideaMediaRepository.save(IdeaMedia(
                    id = UUID.randomUUID(),
                    ideaId = ideaId,
                    mediaAssetId = assetId,
                    position = index,
                    createdAt = now,
                    updatedAt = now,
                ))
            }
        }

        return updated
    }

    fun delete(ideaId: UUID) {
        ideaMediaRepository.deleteByIdeaId(ideaId)
        ideaRepository.delete(ideaId)
    }

    fun move(ideaId: UUID, groupId: UUID?, position: Int): Idea {
        val idea = ideaRepository.findById(ideaId)
            ?: throw IllegalArgumentException("Idea not found: $ideaId")
        val updated = idea.copy(
            groupId = groupId,
            position = position,
            status = if (groupId != null) IdeaStatus.TODO else IdeaStatus.UNASSIGNED,
            updatedAt = Instant.now(),
        )
        ideaRepository.update(updated)
        return updated
    }

    data class ConvertResult(val post: Post, val platformPosts: List<PlatformPost>)

    fun convertToPost(ideaId: UUID): ConvertResult {
        val idea = ideaRepository.findById(ideaId)
            ?: throw IllegalArgumentException("Idea not found: $ideaId")

        if (idea.postId != null) {
            throw IllegalArgumentException("Idea already converted to post: ${idea.postId}")
        }

        val now = Instant.now()
        val post = Post(
            id = UUID.randomUUID(),
            workspaceId = idea.workspaceId,
            authorId = idea.authorId,
            title = idea.title,
            caption = idea.description,
            firstComment = "",
            internalNotes = "",
            tags = idea.tags,
            categoryId = null,
            scheduledAt = null,
            publishedAt = null,
            createdAt = now,
            updatedAt = now,
        )
        postRepository.save(post)

        val ideaMediaList = ideaMediaRepository.findByIdeaId(ideaId)
        ideaMediaList.forEach { im ->
            postMediaRepository.save(PostMedia(
                id = UUID.randomUUID(),
                postId = post.id,
                mediaAssetId = im.mediaAssetId,
                position = im.position,
                altText = "",
                platformOverrides = null,
            ))
        }

        val accounts = socialAccountRepository.findActiveByWorkspace(idea.workspaceId)
        val platformPosts = accounts.map { account ->
            val pp = PlatformPost(
                id = UUID.randomUUID(),
                postId = post.id,
                socialAccountId = account.id,
                platformTitle = null,
                platformCaption = null,
                platformFirstComment = null,
                platformMedia = null,
                platformExtra = null,
                status = PlatformPostStatus.DRAFT,
                platformPostId = "",
                publishError = "",
                publishedAt = null,
                scheduledAt = null,
                retryCount = 0,
                nextRetryAt = null,
                createdAt = now,
                updatedAt = now,
            )
            platformPostRepository.save(pp)
            pp
        }

        ideaRepository.update(idea.copy(postId = post.id, updatedAt = now))

        return ConvertResult(post, platformPosts)
    }
}
