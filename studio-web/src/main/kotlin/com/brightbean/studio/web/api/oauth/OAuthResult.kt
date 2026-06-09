package com.brightbean.studio.web.api.oauth

import java.util.UUID

data class OAuthResult(
    val socialAccountId: UUID,
    val workspaceId: UUID,
    val platformUserId: String,
    val username: String,
)