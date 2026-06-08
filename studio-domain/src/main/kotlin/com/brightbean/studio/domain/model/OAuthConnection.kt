package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class OAuthConnection(
    val id: UUID,
    val userId: UUID,
    val provider: String,
    val providerUserId: String,
    val providerEmail: String? = null,
    val createdAt: Instant = Instant.now(),
)
