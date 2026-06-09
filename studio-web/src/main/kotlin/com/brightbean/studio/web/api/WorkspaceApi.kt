package com.brightbean.studio.web.api

import com.brightbean.studio.web.api.dto.ErrorResponse
import com.brightbean.studio.web.api.dto.WorkspaceResponse
import com.brightbean.studio.web.api.dto.toResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.brightbean.studio.domain.repository.WorkspaceRepository
import java.util.UUID

class WorkspaceApi(
    private val workspaceRepository: WorkspaceRepository,
) : HttpHandler {

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+$")) && method == "GET" -> getWorkspace(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun getWorkspace(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[4])

            val workspace = workspaceRepository.findById(workspaceId)
            if (workspace == null) {
                sendError(exchange, 404, "Workspace not found")
                return
            }

            sendJson(exchange, 200, workspace.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any) {
        val json = com.google.gson.Gson().toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(
            error = when (statusCode) {
                400 -> "Bad Request"
                404 -> "Not Found"
                500 -> "Internal Server Error"
                else -> "Error"
            },
            message = message,
            statusCode = statusCode,
        )
        sendJson(exchange, statusCode, error)
    }
}
