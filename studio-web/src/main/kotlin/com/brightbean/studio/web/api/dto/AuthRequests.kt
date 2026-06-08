package com.brightbean.studio.web.api.dto

data class RegisterRequest(
    val email: String,
    val name: String,
    val password: String,
)

data class LoginRequest(
    val email: String,
    val password: String,
)
