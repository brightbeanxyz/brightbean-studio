package com.brightbean.studio.infrastructure.provider

data class PlatformProfile(
    val platformUserId: String,
    val platformUsername: String,
    val platformDisplayName: String,
    val platformAvatarUrl: String? = null,
    val profileUrl: String? = null,
    val metadata: Map<String, String> = emptyMap(),
)
