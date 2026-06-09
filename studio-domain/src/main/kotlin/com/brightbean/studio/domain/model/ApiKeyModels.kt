package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class ApiKey(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val lookupPrefix: String,
    val tokenHash: String,
    val permissions: String,
    val socialAccountIds: String,
    val issuedBy: UUID?,
    val expiresAt: Instant?,
    val revokedAt: Instant?,
    val lastUsedAt: Instant?,
    val lastUsedIp: String?,
    val rateOverrideWrites: Int?,
    val rateOverrideReads: Int?,
    val createdAt: Instant,
) {
    val isActive: Boolean get() = revokedAt == null && (expiresAt == null || !Instant.now().isAfter(expiresAt))
}

data class ApiKeyAuditLog(
    val id: UUID,
    val apiKeyId: UUID,
    val action: String,
    val targetId: UUID?,
    val method: String,
    val path: String,
    val statusCode: Int,
    val ip: String?,
    val userAgent: String,
    val createdAt: Instant,
)
