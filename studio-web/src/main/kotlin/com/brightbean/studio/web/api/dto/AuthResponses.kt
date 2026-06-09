package com.brightbean.studio.web.api.dto

import java.util.UUID

data class AuthResponse(
    val token: String,
    val user: UserResponse,
)

data class UserResponse(
    val id: UUID,
    val email: String,
    val name: String,
    val avatar: String?,
)
