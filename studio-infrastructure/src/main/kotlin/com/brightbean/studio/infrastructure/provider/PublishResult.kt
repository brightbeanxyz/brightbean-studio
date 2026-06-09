package com.brightbean.studio.infrastructure.provider

import java.time.Instant
import java.util.UUID

data class PublishResult(
    val success: Boolean,
    val platformPostId: String? = null,
    val postUrl: String? = null,
    val publishedAt: Instant? = null,
    val errorMessage: String? = null,
)
