package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.AnalyticsUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class AnalyticsApi(
    private val analyticsUseCases: AnalyticsUseCases,
) : HttpHandler {

    private val gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/analytics/posts/[^/]+$")) && method == "GET" -> getPostMetrics(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/analytics/[^/]+$")) && method == "GET" -> getAccountAnalytics(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun getAccountAnalytics(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(parts[3])
            val accountId = UUID.fromString(parts[5])
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val days = params["days"]?.toIntOrNull() ?: 30
            val metric = params["metric"]

            if (metric != null) {
                val series = analyticsUseCases.getAccountSeries(accountId, metric, days)
                sendJson(exchange, 200, mapOf("series" to series))
            } else {
                val kpis = analyticsUseCases.getAccountKpiCards(accountId, days)
                sendJson(exchange, 200, kpis)
            }
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to get account analytics")
        }
    }

    private fun getPostMetrics(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val postId = UUID.fromString(parts.last())
            val metrics = analyticsUseCases.getPostMetrics(postId)
            sendJson(exchange, 200, mapOf("metrics" to metrics))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to get post metrics")
        }
    }

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
