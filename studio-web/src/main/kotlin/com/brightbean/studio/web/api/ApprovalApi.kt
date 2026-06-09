package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.ApprovalUseCases
import com.brightbean.studio.application.usecase.CommentUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class ApprovalApi(
    private val approvalUseCases: ApprovalUseCases,
    private val commentUseCases: CommentUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/submit$")) && method == "POST" -> submitForReview(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/[^/]+/approve$")) && method == "POST" -> approve(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/[^/]+/request-changes$")) && method == "POST" -> requestChanges(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/[^/]+/reject$")) && method == "POST" -> reject(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/[^/]+/resubmit$")) && method == "POST" -> resubmit(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/bulk-approve$")) && method == "POST" -> bulkApprove(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/bulk-reject$")) && method == "POST" -> bulkReject(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/posts/[^/]+/comments$")) && method == "GET" -> getComments(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/approvals/posts/[^/]+/comments$")) && method == "POST" -> createComment(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun submitForReview(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val request = approvalUseCases.submitForReview(workspaceId, UUID.fromString(req["postId"] as String), UUID.fromString(req["requestedBy"] as String))
            sendJson(exchange, 201, request)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to submit for review")
        }
    }

    private fun approve(exchange: HttpExchange) {
        try {
            val requestId = extractUuidBeforeSegment(exchange, "approve")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val request = approvalUseCases.approve(requestId, UUID.fromString(req["reviewerId"] as String), req["comment"] as? String ?: "")
            sendJson(exchange, 200, request)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to approve")
        }
    }

    private fun requestChanges(exchange: HttpExchange) {
        try {
            val requestId = extractUuidBeforeSegment(exchange, "request-changes")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val request = approvalUseCases.requestChanges(requestId, UUID.fromString(req["reviewerId"] as String), req["comment"] as String)
            sendJson(exchange, 200, request)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to request changes")
        }
    }

    private fun reject(exchange: HttpExchange) {
        try {
            val requestId = extractUuidBeforeSegment(exchange, "reject")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val request = approvalUseCases.reject(requestId, UUID.fromString(req["reviewerId"] as String), req["comment"] as String)
            sendJson(exchange, 200, request)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to reject")
        }
    }

    private fun resubmit(exchange: HttpExchange) {
        try {
            val requestId = extractUuidBeforeSegment(exchange, "resubmit")
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val request = approvalUseCases.resubmit(requestId, UUID.fromString(req["userId"] as String), req["comment"] as? String ?: "")
            sendJson(exchange, 200, request)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to resubmit")
        }
    }

    private fun bulkApprove(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            @Suppress("UNCHECKED_CAST")
            val ids = (req["requestIds"] as List<String>).map { UUID.fromString(it) }
            val reviewerId = UUID.fromString(req["reviewerId"] as String)
            val results = approvalUseCases.bulkApprove(ids, reviewerId)
            sendJson(exchange, 200, results)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to bulk approve")
        }
    }

    private fun bulkReject(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            @Suppress("UNCHECKED_CAST")
            val ids = (req["requestIds"] as List<String>).map { UUID.fromString(it) }
            val reviewerId = UUID.fromString(req["reviewerId"] as String)
            val comment = req["comment"] as? String ?: ""
            val results = approvalUseCases.bulkReject(ids, reviewerId, comment)
            sendJson(exchange, 200, results)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to bulk reject")
        }
    }

    private fun getComments(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val postIdIdx = parts.indexOf("posts") + 1
            val postId = UUID.fromString(parts[postIdIdx])
            val comments = commentUseCases.getCommentsForPost(postId)
            sendJson(exchange, 200, comments)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createComment(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val postIdIdx = parts.indexOf("posts") + 1
            val postId = UUID.fromString(parts[postIdIdx])
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val comment = commentUseCases.createComment(postId, req["authorId"]?.toString()?.let { UUID.fromString(it) }, req["body"] as String, req["visibility"] as? String ?: "internal")
            sendJson(exchange, 201, comment)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create comment")
        }
    }

    private fun extractWorkspaceId(exchange: HttpExchange): UUID = UUID.fromString(exchange.requestURI.path.split("/")[3])
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
}
