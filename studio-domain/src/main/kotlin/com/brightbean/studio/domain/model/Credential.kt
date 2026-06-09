package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Credential(
    val id: UUID,
    val workspaceId: UUID,
    val platformType: PlatformType,
    val encryptedAccessToken: String,
    val encryptedRefreshToken: String? = null,
    val tokenExpiresAt: Instant? = null,
    val metadata: Map<String, String> = emptyMap(),
    val createdAt: Instant,
    val updatedAt: Instant,
)
