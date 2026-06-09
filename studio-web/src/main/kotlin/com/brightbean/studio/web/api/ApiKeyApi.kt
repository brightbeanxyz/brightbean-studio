package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.ApiKeyUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class ApiKeyApi(
    private val apiKeyUseCases: ApiKeyUseCases,
) : HttpHandler {

    private val gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/api-keys/[^/]+/revoke$")) && method == "POST" -> revokeApiKey(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/api-keys$")) && method == "POST" -> issueApiKey(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/api-keys$")) && method == "GET" -> listApiKeys(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listApiKeys(exchange: HttpExchange) {
        try {
            val orgId = extractOrgId(exchange)
            val keys = apiKeyUseCases.listApiKeys(orgId)
            sendJson(exchange, 200, mapOf("keys" to keys))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to list API keys")
        }
    }

    private fun issueApiKey(exchange: HttpExchange) {
        try {
            val orgId = extractOrgId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val name = req["name"] as String
            @Suppress("UNCHECKED_CAST")
            val permissions = (req["permissions"] as? List<String>) ?: emptyList()
            @Suppress("UNCHECKED_CAST")
            val socialAccountIds = (req["socialAccountIds"] as? List<String>)?.map { UUID.fromString(it) } ?: emptyList()
            val issuedBy = req["issuedBy"]?.toString()?.let { UUID.fromString(it) }
            val expiresAt = req["expiresAt"]?.toString()?.let { Instant.parse(it) }

            val result = apiKeyUseCases.issueApiKey(orgId, name, permissions, socialAccountIds, issuedBy, expiresAt)
            sendJson(exchange, 201, mapOf(
                "apiKey" to result.apiKey,
                "rawToken" to result.rawToken,
            ))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to issue API key")
        }
    }

    private fun revokeApiKey(exchange: HttpExchange) {
        try {
            val parts = exchange.requestURI.path.split("/")
            val keyId = UUID.fromString(parts[parts.indexOf("api-keys") + 1])
            apiKeyUseCases.revokeApiKey(keyId)
            sendJson(exchange, 200, mapOf("revoked" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to revoke API key")
        }
    }

    private fun extractOrgId(exchange: HttpExchange): UUID = UUID.fromString(exchange.requestURI.path.split("/")[3])

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
