package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.PostTemplateUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class TemplateApi(
    private val templateUseCases: PostTemplateUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/templates$")) && method == "GET" -> listTemplates(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/templates$")) && method == "POST" -> createTemplate(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/templates/[^/]+$")) && method == "DELETE" -> deleteTemplate(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listTemplates(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val templates = templateUseCases.list(workspaceId)
            sendJson(exchange, 200, templates)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createTemplate(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateTemplateRequest::class.java)

            val template = templateUseCases.saveAsTemplate(
                workspaceId = workspaceId,
                name = request.name,
                description = request.description ?: "",
                templateData = request.templateData,
                createdBy = null,
            )
            sendJson(exchange, 201, template)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create template")
        }
    }

    private fun deleteTemplate(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val templateId = UUID.fromString(pathParts[5])

            templateUseCases.delete(templateId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete template")
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

    private data class CreateTemplateRequest(
        val name: String,
        val description: String? = null,
        val templateData: String,
    )
}
