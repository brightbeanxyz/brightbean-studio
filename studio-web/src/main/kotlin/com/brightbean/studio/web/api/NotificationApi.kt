package com.brightbean.studio.web.api

import com.brightbean.studio.application.service.NotificationEngine
import com.brightbean.studio.application.service.NotificationUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class NotificationApi(
    private val notificationUseCases: NotificationUseCases,
    private val notificationEngine: NotificationEngine,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/notifications$")) && method == "GET" -> listNotifications(exchange)
            path.matches(Regex("^/api/notifications/[^/]+/read$")) && method == "PUT" -> markAsRead(exchange)
            path.matches(Regex("^/api/notifications/read-all$")) && method == "PUT" -> markAllRead(exchange)
            path.matches(Regex("^/api/notifications/unread-count$")) && method == "GET" -> getUnreadCount(exchange)
            path.matches(Regex("^/api/notifications/preferences$")) && method == "GET" -> getPreferences(exchange)
            path.matches(Regex("^/api/notifications/preferences$")) && method == "PUT" -> updatePreference(exchange)
            path.matches(Regex("^/api/notifications/quiet-hours$")) && method == "GET" -> getQuietHours(exchange)
            path.matches(Regex("^/api/notifications/quiet-hours$")) && method == "PUT" -> updateQuietHours(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listNotifications(exchange: HttpExchange) {
        try {
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val userId = UUID.fromString(params["userId"] ?: throw IllegalArgumentException("userId required"))
            val notifications = notificationUseCases.listByUser(userId)
            sendJson(exchange, 200, notifications)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to list notifications")
        }
    }

    private fun markAsRead(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val notificationId = UUID.fromString(parts[parts.indexOf("notifications") + 1])
            val notification = notificationUseCases.markAsRead(notificationId)
            if (notification != null) sendJson(exchange, 200, notification) else sendError(exchange, 404, "Notification not found")
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to mark as read")
        }
    }

    private fun markAllRead(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val userId = UUID.fromString(req["userId"] as String)
            notificationUseCases.markAllRead(userId)
            sendJson(exchange, 200, mapOf("marked" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to mark all as read")
        }
    }

    private fun getUnreadCount(exchange: HttpExchange) {
        try {
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val userId = UUID.fromString(params["userId"] ?: throw IllegalArgumentException("userId required"))
            val count = notificationUseCases.getUnreadCount(userId)
            sendJson(exchange, 200, mapOf("count" to count))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to get unread count")
        }
    }

    private fun getPreferences(exchange: HttpExchange) {
        try {
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val userId = UUID.fromString(params["userId"] ?: throw IllegalArgumentException("userId required"))
            sendJson(exchange, 200, notificationUseCases.getPreferences(userId))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to get preferences")
        }
    }

    private fun updatePreference(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val pref = com.brightbean.studio.domain.model.NotificationPreference(
                id = UUID.fromString(req["id"] as String),
                userId = UUID.fromString(req["userId"] as String),
                eventType = com.brightbean.studio.domain.model.EventType.valueOf(req["eventType"] as String),
                channel = com.brightbean.studio.domain.model.NotificationChannel.valueOf(req["channel"] as String),
                isEnabled = req["isEnabled"] as Boolean,
            )
            sendJson(exchange, 200, notificationUseCases.updatePreference(pref))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update preference")
        }
    }

    private fun getQuietHours(exchange: HttpExchange) {
        try {
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val userId = UUID.fromString(params["userId"] ?: throw IllegalArgumentException("userId required"))
            val qh = notificationUseCases.getQuietHours(userId)
            sendJson(exchange, 200, qh)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to get quiet hours")
        }
    }

    private fun updateQuietHours(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val qh = com.brightbean.studio.domain.model.QuietHours(
                id = UUID.fromString(req["id"] as String),
                userId = UUID.fromString(req["userId"] as String),
                isEnabled = req["isEnabled"] as Boolean,
                startTime = req["startTime"]?.toString()?.let { java.time.LocalTime.parse(it) },
                endTime = req["endTime"]?.toString()?.let { java.time.LocalTime.parse(it) },
                timezone = req["timezone"] as? String ?: "UTC",
                digestMode = req["digestMode"] as? Boolean ?: false,
            )
            sendJson(exchange, 200, notificationUseCases.updateQuietHours(qh))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update quiet hours")
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

    private fun parseQueryParams(query: String): Map<String, String> {
        if (query.isBlank()) return emptyMap()
        return query.split("&").mapNotNull { val p = it.split("="); if (p.size == 2) p[0] to p[1] else null }.toMap()
    }
}
