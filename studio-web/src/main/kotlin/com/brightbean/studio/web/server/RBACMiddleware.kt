package com.brightbean.studio.web.server

import com.brightbean.studio.application.auth.RbacContext
import com.brightbean.studio.application.auth.RbacResolver
import com.brightbean.studio.application.usecase.AuthUseCases
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.util.UUID

class RBACMiddleware(
    private val authUseCases: AuthUseCases,
    private val rbacResolver: RbacResolver,
    private val publicPaths: Set<String>,
    private val next: HttpHandler,
) : HttpHandler {
    companion object {
        const val BEARER_PREFIX = "Bearer "
        const val RBAC_CONTEXT_ATTR = "rbac.context"
        private val WORKSPACE_ID_PATTERN = Regex("/api/workspaces/([^/]+)")
        private val ORG_ID_PATTERN = Regex("/api/orgs/([^/]+)")
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

        val workspaceId = extractWorkspaceId(path)
        val orgId = extractOrgId(path)
        val context = rbacResolver.resolve(user, workspaceId, orgId)

        if (workspaceId != null && context.workspaceMembership == null) {
            sendForbidden(exchange, "You do not have access to this workspace")
            return
        }

        exchange.setAttribute(RBAC_CONTEXT_ATTR, context)
        next.handle(exchange)
    }

    private fun isPublicPath(path: String): Boolean {
        return publicPaths.any { prefix -> path == prefix || path.startsWith("$prefix/") }
    }

    private fun extractWorkspaceId(path: String): UUID? {
        val match = WORKSPACE_ID_PATTERN.find(path) ?: return null
        return try { UUID.fromString(match.groupValues[1]) } catch (_: Exception) { null }
    }

    private fun extractOrgId(path: String): UUID? {
        val match = ORG_ID_PATTERN.find(path) ?: return null
        return try { UUID.fromString(match.groupValues[1]) } catch (_: Exception) { null }
    }

    private fun sendUnauthorized(exchange: HttpExchange, message: String) {
        val response = """{"error":"Unauthorized","message":"$message","statusCode":401}"""
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(401, response.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(response.toByteArray()) }
    }

    private fun sendForbidden(exchange: HttpExchange, message: String) {
        val response = """{"error":"Forbidden","message":"$message","statusCode":403}"""
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(403, response.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(response.toByteArray()) }
    }
}
