package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class StaticPage(
    val id: UUID,
    val title: String,
    val content: String,
    val slug: String,
    val createdAt: Instant,
    val updatedAt: Instant,
)
