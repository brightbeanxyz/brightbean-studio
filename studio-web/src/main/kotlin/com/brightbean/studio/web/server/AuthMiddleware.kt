package com.brightbean.studio.web.server

import com.brightbean.studio.application.usecase.AuthUseCases
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler

class AuthMiddleware(
    private val authUseCases: AuthUseCases,
    private val publicPaths: Set<String>,
    private val next: HttpHandler,
) : HttpHandler {
    companion object {
        const val BEARER_PREFIX = "Bearer "
        const val AUTH_ATTR = "auth.user"
    }

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        if (isPublicPath(path)) {
            next.handle(exchange)
            return
        }
        val authHeader = exchange.requestHeaders.getFirst("Authorization") ?: ""
        if (!authHeader.startsWith(BEARER_PREFIX)) {
            sendUnauthorized(exchange, "Missing or invalid Authorization header")
            return
        }
        val token = authHeader.substring(BEARER_PREFIX.length)
        val user = authUseCases.verifySession(token)
        if (user == null) {
            sendUnauthorized(exchange, "Invalid or expired session")
            return
        }
        exchange.setAttribute(AUTH_ATTR, user)
        next.handle(exchange)
    }

    private fun isPublicPath(path: String): Boolean {
        return publicPaths.any { prefix -> path == prefix || path.startsWith("$prefix/") || path == "$prefix" }
    }

    private fun sendUnauthorized(exchange: HttpExchange, message: String) {
        val response = """{"error":"Unauthorized","message":"$message","statusCode":401}"""
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(401, response.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(response.toByteArray()) }
    }
}
