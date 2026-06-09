package com.brightbean.studio.domain.model

import java.time.Instant

data class AnalyticsPlatformConfig(
    val platform: String,
    val isEnabled: Boolean = true,
    val updatedAt: Instant,
)
