package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class SocialAccount(
    val id: UUID,
    val workspaceId: UUID,
    val credentialId: UUID,
    val platformType: PlatformType,
    val platformUserId: String,
    val platformUsername: String,
    val platformDisplayName: String,
    val platformAvatarUrl: String? = null,
    val profileUrl: String? = null,
    val isActive: Boolean = true,
    val connectionStatus: ConnectionStatus = ConnectionStatus.CONNECTED,
    val lastHealthCheckAt: Instant? = null,
    val lastError: String? = null,
    val followerCount: Int = 0,
    val instanceUrl: String? = null,
    val dailyPostLimitOverride: Int? = null,
    val analyticsNeedsReconnect: Boolean = false,
    val metadata: Map<String, String> = emptyMap(),
    val connectedAt: Instant,
    val lastSyncAt: Instant? = null,
)
