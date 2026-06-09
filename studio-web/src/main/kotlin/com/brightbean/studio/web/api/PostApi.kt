package com.brightbean.studio.web.api

import com.brightbean.studio.application.auth.WorkspacePermissionKeys
import com.brightbean.studio.application.usecase.CreatePostUseCase
import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.application.usecase.SchedulePostUseCase
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.web.api.dto.CreatePostRequest
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.brightbean.studio.web.api.dto.PaginatedResponse
import com.brightbean.studio.web.api.dto.PostResponse
import com.brightbean.studio.web.api.dto.SchedulePostRequest
import com.brightbean.studio.web.api.dto.toResponse
import com.brightbean.studio.web.server.PermissionChecks
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.stream.JsonReader
import com.google.gson.stream.JsonToken
import com.google.gson.stream.JsonWriter

class PostApi(
    private val createPostUseCase: CreatePostUseCase,
    private val schedulePostUseCase: SchedulePostUseCase,
    private val publishPostUseCase: PublishPostUseCase,
    private val postRepository: PostRepository,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/posts$")) && method == "GET" -> listPosts(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/posts$")) && method == "POST" -> createPost(exchange)
            path.matches(Regex("^/api/posts/[^/]+/publish$")) && method == "POST" -> publishPost(exchange)
            path.matches(Regex("^/api/posts/[^/]+/schedule$")) && method == "POST" -> schedulePost(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listPosts(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val queryParams = parseQueryParams(exchange.requestURI.query ?: "")
            val page = queryParams["page"]?.toIntOrNull() ?: 1
            val pageSize = queryParams["pageSize"]?.toIntOrNull() ?: 25

            val posts = postRepository.findByWorkspaceId(workspaceId)

            val totalCount = posts.size
            val totalPages = (totalCount + pageSize - 1) / pageSize
            val startIndex = (page - 1) * pageSize
            val paginatedPosts = posts.drop(startIndex).take(pageSize)

            val response = PaginatedResponse(
                items = paginatedPosts.map { it.toResponse() },
                page = page,
                pageSize = pageSize,
                totalCount = totalCount,
                totalPages = totalPages,
            )

            sendJson(exchange, 200, response)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createPost(exchange: HttpExchange) {
        if (!PermissionChecks.hasPermission(exchange, WorkspacePermissionKeys.CREATE_POSTS)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreatePostRequest::class.java)

            val post = createPostUseCase.execute(
                workspaceId = workspaceId,
                authorId = UUID.randomUUID(),
                content = request.content,
                socialAccountIds = emptyList(),
                scheduledAt = request.scheduledAt,
                requiresApproval = request.requiresApproval,
                categoryId = request.categoryId,
                mediaIds = request.mediaIds,
            )

            sendJson(exchange, 201, post.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create post")
        }
    }

    private fun publishPost(exchange: HttpExchange) {
        if (!PermissionChecks.hasPermission(exchange, WorkspacePermissionKeys.PUBLISH_DIRECTLY)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val postId = UUID.fromString(pathParts[3])

            val post = publishPostUseCase.execute(postId)
            sendJson(exchange, 200, post.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to publish post")
        }
    }

    private fun schedulePost(exchange: HttpExchange) {
        if (!PermissionChecks.hasPermission(exchange, WorkspacePermissionKeys.PUBLISH_DIRECTLY)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val postId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, SchedulePostRequest::class.java)

            val post = schedulePostUseCase.execute(postId, request.scheduledFor)

            sendJson(exchange, 200, mapOf(
                "postId" to post.id,
                "post" to post.toResponse()
            ))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to schedule post")
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

    private fun parseQueryParams(query: String): Map<String, String> {
        if (query.isBlank()) return emptyMap()
        return query.split("&")
            .mapNotNull { param ->
                val parts = param.split("=")
                if (parts.size == 2) parts[0] to parts[1] else null
            }
            .toMap()
    }
}

class InstantAdapter : com.google.gson.TypeAdapter<Instant>() {
    override fun write(out: JsonWriter, value: Instant?) {
        if (value == null) {
            out.nullValue()
        } else {
            out.value(value.toString())
        }
    }

    override fun read(input: JsonReader): Instant? {
        return if (input.peek() == JsonToken.NULL) {
            input.nextNull()
            null
        } else {
            Instant.parse(input.nextString())
        }
    }
}
