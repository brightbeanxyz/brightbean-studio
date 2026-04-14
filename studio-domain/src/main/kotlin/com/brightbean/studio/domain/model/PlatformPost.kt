package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class PlatformPost(
    val id: UUID,
    val postId: UUID,
    val socialAccountId: UUID,
    val platformPostId: String?,
    val platformUrl: String?,
    val status: PostStatus,
    val errorMessage: String?,
    val publishedAt: Instant?,
)
