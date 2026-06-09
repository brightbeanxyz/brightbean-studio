package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.ContentCategoryUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class CategoryApi(
    private val categoryUseCases: ContentCategoryUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/categories$")) && method == "GET" -> listCategories(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/categories$")) && method == "POST" -> createCategory(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/categories/[^/]+$")) && method == "PUT" -> updateCategory(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/categories/[^/]+$")) && method == "DELETE" -> deleteCategory(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listCategories(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val categories = categoryUseCases.list(workspaceId)
            sendJson(exchange, 200, categories)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createCategory(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateCategoryRequest::class.java)

            val category = categoryUseCases.create(workspaceId, request.name, request.color)
            sendJson(exchange, 201, category)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create category")
        }
    }

    private fun updateCategory(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val categoryId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateCategoryRequest::class.java)

            val category = categoryUseCases.update(categoryId, request.name, request.color)
            sendJson(exchange, 200, category)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update category")
        }
    }

    private fun deleteCategory(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val categoryId = UUID.fromString(pathParts[5])

            categoryUseCases.delete(categoryId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete category")
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

    private data class CreateCategoryRequest(val name: String, val color: String)
    private data class UpdateCategoryRequest(val name: String? = null, val color: String? = null)
}
