package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.TransitionPlatformPostUseCase
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class PlatformPostTransitionApi(
    private val transitionUseCase: TransitionPlatformPostUseCase,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/posts/[^/]+/platform-posts/[^/]+/transition$")) && method == "POST" -> transition(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun transition(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val platformPostId = UUID.fromString(pathParts[7])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, TransitionRequest::class.java)

            val targetStatus = try {
                PlatformPostStatus.valueOf(request.targetStatus)
            } catch (e: IllegalArgumentException) {
                sendError(exchange, 400, "Invalid status: ${request.targetStatus}"); return
            }

            val updated = transitionUseCase.execute(platformPostId, targetStatus, request.scheduledAt)
            sendJson(exchange, 200, updated)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to transition platform post")
        }
    }

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(
            error = when (statusCode) {
                400 -> "Bad Request"
                403 -> "Forbidden"
                404 -> "Not Found"
                500 -> "Internal Server Error"
                else -> "Error"
            },
            message = message,
            statusCode = statusCode,
        )
        sendJson(exchange, statusCode, error)
    }

    private data class TransitionRequest(
        val targetStatus: String,
        val scheduledAt: Instant? = null,
    )
}
