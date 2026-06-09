package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.IdeaGroupUseCases
import com.brightbean.studio.application.usecase.IdeaUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class IdeaApi(
    private val ideaUseCases: IdeaUseCases,
    private val ideaGroupUseCases: IdeaGroupUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/ideas$")) && method == "GET" -> listIdeas(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/ideas$")) && method == "POST" -> createIdea(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/ideas/[^/]+$")) && method == "PUT" -> updateIdea(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/ideas/[^/]+$")) && method == "DELETE" -> deleteIdea(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/ideas/[^/]+/move$")) && method == "POST" -> moveIdea(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/ideas/[^/]+/convert$")) && method == "POST" -> convertIdea(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/idea-groups$")) && method == "GET" -> listGroups(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/idea-groups$")) && method == "POST" -> createGroup(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/idea-groups/[^/]+$")) && method == "DELETE" -> deleteGroup(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/idea-groups/reorder$")) && method == "POST" -> reorderGroups(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listIdeas(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val ideas = ideaUseCases.listByWorkspace(workspaceId)
            sendJson(exchange, 200, ideas)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createIdea(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateIdeaRequest::class.java)

            val idea = ideaUseCases.create(
                workspaceId = workspaceId,
                authorId = null,
                title = request.title,
                description = request.description,
                tags = request.tags ?: emptyList(),
                mediaAssetIds = request.mediaAssetIds ?: emptyList(),
                groupId = request.groupId,
            )
            sendJson(exchange, 201, idea)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create idea")
        }
    }

    private fun updateIdea(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val ideaId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateIdeaRequest::class.java)

            val idea = ideaUseCases.update(
                ideaId = ideaId,
                title = request.title,
                description = request.description,
                tags = request.tags,
                groupId = request.groupId,
                mediaAssetIds = request.mediaAssetIds,
            )
            sendJson(exchange, 200, idea)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update idea")
        }
    }

    private fun deleteIdea(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val ideaId = UUID.fromString(pathParts[5])

            ideaUseCases.delete(ideaId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete idea")
        }
    }

    private fun moveIdea(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val ideaId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, MoveIdeaRequest::class.java)

            val idea = ideaUseCases.move(ideaId, request.groupId, request.position)
            sendJson(exchange, 200, idea)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to move idea")
        }
    }

    private fun convertIdea(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val ideaId = UUID.fromString(pathParts[5])

            val result = ideaUseCases.convertToPost(ideaId)
            sendJson(exchange, 200, mapOf(
                "post" to result.post,
                "platformPosts" to result.platformPosts,
            ))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to convert idea")
        }
    }

    private fun listGroups(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val groups = ideaGroupUseCases.list(workspaceId)
            sendJson(exchange, 200, groups)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createGroup(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateGroupRequest::class.java)

            val group = ideaGroupUseCases.create(workspaceId, request.name)
            sendJson(exchange, 201, group)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create group")
        }
    }

    private fun deleteGroup(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val groupId = UUID.fromString(pathParts[5])

            ideaGroupUseCases.delete(groupId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete group")
        }
    }

    private fun reorderGroups(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, ReorderGroupsRequest::class.java)

            ideaGroupUseCases.reorder(request.orderedIds)
            sendJson(exchange, 200, mapOf("reordered" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to reorder groups")
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

    private data class CreateIdeaRequest(
        val title: String,
        val description: String,
        val tags: List<String>? = null,
        val mediaAssetIds: List<UUID>? = null,
        val groupId: UUID? = null,
    )

    private data class UpdateIdeaRequest(
        val title: String? = null,
        val description: String? = null,
        val tags: List<String>? = null,
        val groupId: UUID? = null,
        val mediaAssetIds: List<UUID>? = null,
    )

    private data class MoveIdeaRequest(
        val groupId: UUID?,
        val position: Int,
    )

    private data class CreateGroupRequest(val name: String)

    private data class ReorderGroupsRequest(val orderedIds: List<UUID>)
}
