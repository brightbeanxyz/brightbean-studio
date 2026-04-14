package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class BlogPost(
    val id: UUID,
    val title: String,
    val content: String,
    val excerpt: String,
    val slug: String,
    val authorId: UUID,
    val tags: List<String>,
    val publishedAt: Instant?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
