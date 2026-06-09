package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.FeedUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class FeedApi(
    private val feedUseCases: FeedUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/feeds$")) && method == "GET" -> listFeeds(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/feeds$")) && method == "POST" -> addFeed(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/feeds/[^/]+$")) && method == "DELETE" -> deleteFeed(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listFeeds(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val feeds = feedUseCases.list(workspaceId)
            sendJson(exchange, 200, feeds)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun addFeed(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, AddFeedRequest::class.java)

            val feed = feedUseCases.add(
                workspaceId = workspaceId,
                name = request.name,
                url = request.url,
                websiteUrl = request.websiteUrl ?: "",
                addedBy = null,
            )
            sendJson(exchange, 201, feed)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to add feed")
        }
    }

    private fun deleteFeed(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val feedId = UUID.fromString(pathParts[5])

            feedUseCases.delete(feedId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete feed")
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

    private data class AddFeedRequest(
        val name: String,
        val url: String,
        val websiteUrl: String? = null,
    )
}
