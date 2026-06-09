package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.CreateOrganizationUseCase
import com.brightbean.studio.application.usecase.UpdateOrganizationUseCase
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.Organization
import com.brightbean.studio.domain.repository.OrganizationRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import com.brightbean.studio.web.server.PermissionChecks
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class OrganizationApi(
    private val createOrganizationUseCase: CreateOrganizationUseCase,
    private val updateOrganizationUseCase: UpdateOrganizationUseCase,
    private val organizationRepository: OrganizationRepository,
    private val workspaceRepository: WorkspaceRepository,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/workspaces$")) && method == "GET" -> listWorkspaces(exchange)
            path.matches(Regex("^/api/orgs/[^/]+$")) && method == "GET" -> getOrganization(exchange)
            path.matches(Regex("^/api/orgs/[^/]+$")) && method == "PUT" -> updateOrganization(exchange)
            path.matches(Regex("^/api/orgs$")) && method == "POST" -> createOrganization(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun createOrganization(exchange: HttpExchange) {
        try {
            val context = PermissionChecks.getRbacContext(exchange)
                ?: run { sendError(exchange, 401, "Authentication required"); return }
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateOrgRequest::class.java)
            val result = createOrganizationUseCase.execute(context.user.id, request.name, request.defaultTimezone ?: "UTC")
            if (result.isFailure) {
                sendError(exchange, 400, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            val org = result.getOrNull()!!
            sendJson(exchange, 201, org.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun getOrganization(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.MEMBER)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val org = organizationRepository.findById(orgId)
                ?: run { sendError(exchange, 404, "Organization not found"); return }
            sendJson(exchange, 200, org.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun updateOrganization(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateOrgRequest::class.java)
            val result = updateOrganizationUseCase.execute(orgId, request.name, request.defaultTimezone, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            sendJson(exchange, 200, result.getOrNull()!!.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun listWorkspaces(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.MEMBER)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val workspaces = workspaceRepository.findByOrganizationId(orgId)
            sendJson(exchange, 200, workspaces.map { mapOf(
                "id" to it.id.toString(),
                "name" to it.name,
                "slug" to it.slug,
                "isArchived" to it.isArchived,
            ) })
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun Organization.toResponse() = mapOf(
        "id" to id.toString(),
        "name" to name,
        "logoUrl" to logoUrl,
        "defaultTimezone" to defaultTimezone,
        "billingEmail" to billingEmail,
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

data class CreateOrgRequest(val name: String, val defaultTimezone: String? = null)
data class UpdateOrgRequest(val name: String? = null, val defaultTimezone: String? = null)
