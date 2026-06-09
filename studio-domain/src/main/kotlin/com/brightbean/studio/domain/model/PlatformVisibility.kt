package com.brightbean.studio.domain.model

import java.time.Instant

data class PlatformVisibility(
    val platform: String,
    val isVisible: Boolean = true,
    val updatedAt: Instant,
)
