package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class User(
    val id: UUID,
    val email: String,
    val name: String,
    val passwordHash: String,
    val avatar: String? = null,
    val totpSecret: String? = null,
    val totpRecoveryCodes: List<String>? = null,
    val totpEnabled: Boolean = false,
    val lastWorkspaceId: UUID? = null,
    val tosAcceptedAt: Instant? = null,
    val isActive: Boolean = true,
    val createdAt: Instant,
    val updatedAt: Instant,
)
