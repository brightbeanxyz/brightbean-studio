package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Session(
    val id: UUID,
    val userId: UUID,
    val tokenHash: String,
    val deviceInfo: String? = null,
    val ipAddress: String? = null,
    val expiresAt: Instant,
    val createdAt: Instant = Instant.now(),
) {
    val isExpired: Boolean
        get() = Instant.now().isAfter(expiresAt)
}
