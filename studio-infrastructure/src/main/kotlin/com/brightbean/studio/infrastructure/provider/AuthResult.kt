package com.brightbean.studio.infrastructure.provider

data class AuthResult(
    val success: Boolean,
    val accessToken: String? = null,
    val refreshToken: String? = null,
    val expiresAt: Long? = null,
    val errorMessage: String? = null,
)
