package com.brightbean.studio.infrastructure.provider

import java.time.Instant

data class PostInsights(
    val platformPostId: String,
    val impressions: Long = 0,
    val reach: Long = 0,
    val likes: Long = 0,
    val comments: Long = 0,
    val shares: Long = 0,
    val clicks: Long = 0,
    val engagementRate: Double = 0.0,
    val collectedAt: Instant = Instant.now(),
)
