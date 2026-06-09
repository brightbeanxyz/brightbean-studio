package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.ClientPortalUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class ClientPortalApi(
    private val clientPortalUseCases: ClientPortalUseCases,
) : HttpHandler {

    private val gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/portal/magic-link$")) && method == "POST" -> generateMagicLink(exchange)
            path.matches(Regex("^/api/portal/[^/]+/consume$")) && method == "POST" -> consumeMagicLink(exchange)
            path.matches(Regex("^/api/portal/[^/]+$")) && method == "GET" -> peekMagicLink(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun generateMagicLink(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val workspaceId = UUID.fromString(req["workspaceId"] as String)
            val userId = UUID.fromString(req["userId"] as String)
            val createdBy = UUID.fromString(req["createdBy"] as String)
            val token = clientPortalUseCases.generateMagicLink(workspaceId, userId, createdBy)
            sendJson(exchange, 201, token)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to generate magic link")
        }
    }

    private fun peekMagicLink(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val token = parts.last()
            val link = clientPortalUseCases.peekMagicLink(token)
            if (link != null) sendJson(exchange, 200, link) else sendError(exchange, 404, "Token not found or expired")
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to peek magic link")
        }
    }

    private fun consumeMagicLink(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val token = parts[parts.indexOf("portal") + 1]
            val result = clientPortalUseCases.consumeMagicLink(token)
            sendJson(exchange, 200, result)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to consume magic link")
        }
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
