package com.brightbean.studio.web.api.dto

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.model.Workspace
import java.time.Instant
import java.util.UUID

data class PostResponse(
    val id: UUID,
    val workspaceId: UUID,
    val authorId: UUID?,
    val title: String,
    val caption: String,
    val firstComment: String,
    val internalNotes: String,
    val tags: List<String>,
    val categoryId: UUID?,
    val scheduledAt: Instant?,
    val publishedAt: Instant?,
    val createdAt: Instant,
    val updatedAt: Instant,
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
    title = title,
    caption = caption,
    firstComment = firstComment,
    internalNotes = internalNotes,
    tags = tags,
    categoryId = categoryId,
    scheduledAt = scheduledAt,
    publishedAt = publishedAt,
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
