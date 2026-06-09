package com.brightbean.studio.web.api

import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.PlatformCredential
import com.brightbean.studio.domain.model.TestResult
import com.brightbean.studio.domain.repository.PlatformCredentialRepository
import com.brightbean.studio.web.server.PermissionChecks
import com.google.gson.Gson
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class PlatformCredentialApi(
    private val platformCredentialRepository: PlatformCredentialRepository,
) : HttpHandler {

    private val gson = Gson()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/credentials/[^/]+$")) && method == "PUT" -> upsertCredential(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/credentials/[^/]+$")) && method == "DELETE" -> deleteCredential(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/credentials$")) && method == "GET" -> listCredentials(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listCredentials(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val creds = platformCredentialRepository.findByOrganizationId(orgId)
            sendJson(exchange, 200, creds.map { it.toResponse() })
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun upsertCredential(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val platform = pathParts[5]
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpsertCredentialRequest::class.java)
            val now = Instant.now()

            val existing = platformCredentialRepository.findByOrgAndPlatform(orgId, platform)
            if (existing != null) {
                val updated = existing.copy(
                    credentials = request.credentials,
                    isConfigured = true,
                    testResult = TestResult.UNTESTED,
                    updatedAt = now,
                )
                platformCredentialRepository.update(updated)
                sendJson(exchange, 200, updated.toResponse())
            } else {
                val created = PlatformCredential(
                    id = UUID.randomUUID(),
                    organizationId = orgId,
                    platform = platform,
                    credentials = request.credentials,
                    isConfigured = true,
                    createdAt = now,
                    updatedAt = now,
                )
                platformCredentialRepository.save(created)
                sendJson(exchange, 201, created.toResponse())
            }
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun deleteCredential(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.OWNER)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val platform = pathParts[5]
            val existing = platformCredentialRepository.findByOrgAndPlatform(orgId, platform)
            if (existing == null) {
                sendError(exchange, 404, "Credential not found"); return
            }
            platformCredentialRepository.delete(existing.id)
            sendJson(exchange, 200, mapOf("message" to "Credential deleted"))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun PlatformCredential.toResponse() = mapOf(
        "id" to id.toString(),
        "organizationId" to organizationId.toString(),
        "platform" to platform,
        "isConfigured" to isConfigured,
        "testResult" to testResult.name,
        "testedAt" to testedAt?.toString(),
        "createdAt" to createdAt.toString(),
        "updatedAt" to updatedAt.toString(),
    )

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val json = """{"error":"$statusCode","message":"$message"}"""
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }
}

data class UpsertCredentialRequest(val credentials: String)
