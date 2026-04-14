package com.brightbean.studio.infrastructure.provider

import java.time.Instant

data class Comment(
    val platformCommentId: String,
    val platformPostId: String,
    val authorName: String,
    val authorAvatarUrl: String?,
    val content: String,
    val createdAt: Instant,
    val isLiked: Boolean = false,
    val likeCount: Int = 0,
    val replyCount: Int = 0,
)
