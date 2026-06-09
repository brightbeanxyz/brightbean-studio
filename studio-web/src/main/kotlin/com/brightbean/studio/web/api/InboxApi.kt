package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.InboxUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class InboxApi(
    private val inboxUseCases: InboxUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages$")) && method == "GET" -> listMessages(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages/[^/]+$")) && method == "GET" -> getMessage(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages/[^/]+/reply$")) && method == "POST" -> sendReply(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages/[^/]+/notes$")) && method == "POST" -> addNote(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages/[^/]+/assign$")) && method == "POST" -> assignMessage(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages/[^/]+/status$")) && method == "PUT" -> changeStatus(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/messages/[^/]+/sentiment$")) && method == "PUT" -> changeSentiment(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/bulk$")) && method == "POST" -> bulkAction(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/saved-replies$")) && method == "GET" -> listSavedReplies(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/saved-replies$")) && method == "POST" -> createSavedReply(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/saved-replies/[^/]+$")) && method == "DELETE" -> deleteSavedReply(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/sla$")) && method == "GET" -> getSLAConfig(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/inbox/sla$")) && method == "PUT" -> updateSLAConfig(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listMessages(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val params = parseQueryParams(exchange.requestURI.query ?: "")
            val status = params["status"]?.let { com.brightbean.studio.domain.model.InboxMessageStatus.valueOf(it.uppercase()) }
            val messages = inboxUseCases.listMessages(workspaceId, status)
            sendJson(exchange, 200, messages)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun getMessage(exchange: HttpExchange) {
        try {
            val messageId = extractLastUuid(exchange)
            val message = inboxUseCases.getMessage(messageId)
            if (message != null) sendJson(exchange, 200, message)
            else sendError(exchange, 404, "Message not found")
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun sendReply(exchange: HttpExchange) {
        try {
            val messageId = extractUuidBeforeSegment(exchange, "reply")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val reply = inboxUseCases.sendReply(messageId, req["authorId"]?.toString()?.let { UUID.fromString(it) }, req["body"] as String, req["platformReplyId"] as? String ?: "")
            sendJson(exchange, 201, reply)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to send reply")
        }
    }

    private fun addNote(exchange: HttpExchange) {
        try {
            val messageId = extractUuidBeforeSegment(exchange, "notes")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val note = inboxUseCases.addNote(messageId, req["authorId"]?.toString()?.let { UUID.fromString(it) }, req["body"] as String)
            sendJson(exchange, 201, note)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to add note")
        }
    }

    private fun assignMessage(exchange: HttpExchange) {
        try {
            val messageId = extractUuidBeforeSegment(exchange, "assign")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val userId = req["userId"]?.toString()?.let { UUID.fromString(it) }
            val updated = inboxUseCases.assignMessage(messageId, userId)
            sendJson(exchange, 200, updated)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to assign message")
        }
    }

    private fun changeStatus(exchange: HttpExchange) {
        try {
            val messageId = extractUuidBeforeSegment(exchange, "status")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val status = com.brightbean.studio.domain.model.InboxMessageStatus.valueOf((req["status"] as String).uppercase())
            val updated = inboxUseCases.changeStatus(messageId, status)
            sendJson(exchange, 200, updated)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to change status")
        }
    }

    private fun changeSentiment(exchange: HttpExchange) {
        try {
            val messageId = extractUuidBeforeSegment(exchange, "sentiment")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val updated = inboxUseCases.changeSentiment(messageId, req["sentiment"] as String, req["source"] as? String ?: "manual")
            sendJson(exchange, 200, updated)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to change sentiment")
        }
    }

    private fun bulkAction(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            @Suppress("UNCHECKED_CAST")
            val ids = (req["messageIds"] as List<String>).map { UUID.fromString(it) }
            val action = req["action"] as String
            inboxUseCases.bulkAction(ids, action)
            sendJson(exchange, 200, mapOf("processed" to ids.size))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to perform bulk action")
        }
    }

    private fun listSavedReplies(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            sendJson(exchange, 200, inboxUseCases.listSavedReplies(workspaceId))
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createSavedReply(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val reply = inboxUseCases.createSavedReply(workspaceId, req["title"] as String, req["body"] as String, req["createdBy"]?.toString()?.let { UUID.fromString(it) })
            sendJson(exchange, 201, reply)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create saved reply")
        }
    }

    private fun deleteSavedReply(exchange: HttpExchange) {
        try {
            val id = extractLastUuid(exchange)
            inboxUseCases.deleteSavedReply(id)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete saved reply")
        }
    }

    private fun getSLAConfig(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val config = inboxUseCases.getSLAConfig(workspaceId)
            if (config != null) sendJson(exchange, 200, config) else sendJson(exchange, 200, null)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun updateSLAConfig(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val workspaceId = extractWorkspaceId(exchange)
            val config = com.brightbean.studio.domain.model.InboxSLAConfig(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                targetResponseMinutes = (req["targetResponseMinutes"] as? Number)?.toInt() ?: 60,
                isActive = req["isActive"] as? Boolean ?: true,
                autoResolveOnReply = req["autoResolveOnReply"] as? Boolean ?: false,
            )
            val updated = inboxUseCases.updateSLAConfig(config)
            sendJson(exchange, 200, updated)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update SLA config")
        }
    }

    private fun extractWorkspaceId(exchange: HttpExchange): UUID {
        val parts = exchange.requestURI.path.split("/")
        return UUID.fromString(parts[3])
    }

    private fun extractLastUuid(exchange: HttpExchange): UUID {
        val parts = exchange.requestURI.path.split("/")
        return UUID.fromString(parts.last())
    }

    private fun extractUuidBeforeSegment(exchange: HttpExchange, segment: String): UUID {
        val parts = exchange.requestURI.path.split("/")
        val idx = parts.indexOf(segment)
        return UUID.fromString(parts[idx - 1])
    }

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any?) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(error = when (statusCode) { 400 -> "Bad Request"; 404 -> "Not Found"; 500 -> "Internal Server Error"; else -> "Error" }, message = message, statusCode = statusCode)
        sendJson(exchange, statusCode, error)
    }

    private fun parseQueryParams(query: String): Map<String, String> {
        if (query.isBlank()) return emptyMap()
        return query.split("&").mapNotNull { val p = it.split("="); if (p.size == 2) p[0] to p[1] else null }.toMap()
    }
}
