package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.OnboardingUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class OnboardingApi(
    private val onboardingUseCases: OnboardingUseCases,
) : HttpHandler {

    private val gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/connection-links$")) && method == "POST" -> createConnectionLink(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/connection-links/[^/]+/revoke$")) && method == "POST" -> revokeConnectionLink(exchange)
            path.matches(Regex("^/api/connect/[^/]+$")) && method == "GET" -> validateConnectionLink(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/checklist$")) && method == "GET" -> getChecklist(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/checklist/dismiss$")) && method == "POST" -> dismissChecklist(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun createConnectionLink(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val createdBy = req["createdBy"]?.toString()?.let { UUID.fromString(it) }
            val expiresAt = req["expiresAt"]?.toString()?.let { Instant.parse(it) } ?: Instant.now().plusSeconds(7 * 24 * 60 * 60L)
            val link = onboardingUseCases.createConnectionLink(workspaceId, createdBy, expiresAt)
            sendJson(exchange, 201, link)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create connection link")
        }
    }

    private fun revokeConnectionLink(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val linkId = UUID.fromString(parts[parts.indexOf("connection-links") + 1])
            onboardingUseCases.revokeConnectionLink(linkId)
            sendJson(exchange, 200, mapOf("revoked" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to revoke connection link")
        }
    }

    private fun validateConnectionLink(exchange: HttpExchange) {
        try {
            val token = exchange.requestURI.path.split("/").last()
            val link = onboardingUseCases.validateConnectionLink(token)
            if (link != null) sendJson(exchange, 200, link) else sendError(exchange, 404, "Link not found or inactive")
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to validate connection link")
        }
    }

    private fun getChecklist(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val userId = UUID.fromString(params["userId"] ?: throw IllegalArgumentException("userId required"))
            val checklist = onboardingUseCases.getChecklist(userId, workspaceId)
            sendJson(exchange, 200, checklist)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to get checklist")
        }
    }

    private fun dismissChecklist(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val userId = UUID.fromString(req["userId"] as String)
            val checklist = onboardingUseCases.dismissChecklist(userId, workspaceId)
            sendJson(exchange, 200, checklist)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to dismiss checklist")
        }
    }

    private fun extractWorkspaceId(exchange: HttpExchange): UUID = UUID.fromString(exchange.requestURI.path.split("/")[3])

    private fun parseQueryParams(query: String): Map<String, String> {
        if (query.isBlank()) return emptyMap()
        return query.split("&").mapNotNull { val p = it.split("="); if (p.size == 2) p[0] to p[1] else null }.toMap()
    }

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any?) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(error = when (statusCode) { 400 -> "Bad Request"; 404 -> "Not Found"; else -> "Error" }, message = message, statusCode = statusCode)
        sendJson(exchange, statusCode, error)
    }
}
