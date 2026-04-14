package com.brightbean.studio.web.server

data class ServerConfig(
    val host: String = "0.0.0.0",
    val port: Int = 8080,
    val corsOrigins: List<String> = listOf("*"),
)
