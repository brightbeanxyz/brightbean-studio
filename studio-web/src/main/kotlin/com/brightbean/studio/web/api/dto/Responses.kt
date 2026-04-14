package com.brightbean.studio.web.api.dto

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.model.Tag
import com.brightbean.studio.domain.model.Workspace
import java.time.Instant
import java.util.UUID

data class PostResponse(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID,
    val content: String,
    val platforms: List<PlatformType>,
    val categoryId: UUID?,
    val tags: List<TagResponse>,
    val status: PostStatus,
    val scheduledAt: Instant?,
    val publishedAt: Instant?,
    val mediaIds: List<UUID>,
    val createdAt: Instant,
    val updatedAt: Instant,
)

data class TagResponse(
    val id: UUID,
    val name: String,
)

data class SocialAccountResponse(
    val id: UUID,
    val workspaceId: UUID,
    val platformType: PlatformType,
    val platformUsername: String,
    val platformDisplayName: String,
    val platformAvatarUrl: String?,
    val profileUrl: String?,
    val isActive: Boolean,
    val connectedAt: Instant,
    val lastSyncAt: Instant?,
)

data class WorkspaceResponse(
    val id: UUID,
    val name: String,
    val slug: String,
    val ownerId: UUID,
    val createdAt: Instant,
    val updatedAt: Instant,
)

data class PaginatedResponse<T>(
    val items: List<T>,
    val page: Int,
    val pageSize: Int,
    val totalCount: Int,
    val totalPages: Int,
)

data class ErrorResponse(
    val error: String,
    val message: String,
    val statusCode: Int,
)

fun Post.toResponse(): PostResponse = PostResponse(
    id = id,
    workspaceId = workspaceId,
    authorId = authorId,
    content = content,
    platforms = platforms,
    categoryId = categoryId,
    tags = tags.map { TagResponse(id = it.id, name = it.name) },
    status = status,
    scheduledAt = scheduledAt,
    publishedAt = publishedAt,
    mediaIds = mediaIds,
    createdAt = createdAt,
    updatedAt = updatedAt,
)

fun SocialAccount.toResponse(): SocialAccountResponse = SocialAccountResponse(
    id = id,
    workspaceId = workspaceId,
    platformType = platformType,
    platformUsername = platformUsername,
    platformDisplayName = platformDisplayName,
    platformAvatarUrl = platformAvatarUrl,
    profileUrl = profileUrl,
    isActive = isActive,
    connectedAt = connectedAt,
    lastSyncAt = lastSyncAt,
)

fun Workspace.toResponse(): WorkspaceResponse = WorkspaceResponse(
    id = id,
    name = name,
    slug = slug,
    ownerId = ownerId,
    createdAt = createdAt,
    updatedAt = updatedAt,
)
