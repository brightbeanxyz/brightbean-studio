package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.CreateCustomRoleUseCase
import com.brightbean.studio.application.usecase.DeleteCustomRoleUseCase
import com.brightbean.studio.application.usecase.UpdateCustomRoleUseCase
import com.brightbean.studio.domain.model.CustomRole
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.repository.CustomRoleRepository
import com.brightbean.studio.web.server.PermissionChecks
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class CustomRoleApi(
    private val createCustomRoleUseCase: CreateCustomRoleUseCase,
    private val updateCustomRoleUseCase: UpdateCustomRoleUseCase,
    private val deleteCustomRoleUseCase: DeleteCustomRoleUseCase,
    private val customRoleRepository: CustomRoleRepository,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/roles/[^/]+$")) && method == "PUT" -> updateRole(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/roles/[^/]+$")) && method == "DELETE" -> deleteRole(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/roles$")) && method == "GET" -> listRoles(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/roles$")) && method == "POST" -> createRole(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listRoles(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val roles = customRoleRepository.findByOrganizationId(orgId)
            sendJson(exchange, 200, roles.map { it.toResponse() })
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createRole(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateCustomRoleRequest::class.java)
            val permissionsType = object : TypeToken<Map<String, Boolean>>() {}.type
            val permissions: Map<String, Boolean> = gson.fromJson(gson.toJson(request.permissions), permissionsType)
            val result = createCustomRoleUseCase.execute(orgId, request.name, permissions, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            sendJson(exchange, 201, result.getOrNull()!!.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun updateRole(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val roleId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateCustomRoleRequest::class.java)
            val permissions = request.permissions
            val result = updateCustomRoleUseCase.execute(roleId, request.name, permissions, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            sendJson(exchange, 200, result.getOrNull()!!.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun deleteRole(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val roleId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val result = deleteCustomRoleUseCase.execute(roleId, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            sendJson(exchange, 200, mapOf("message" to "Custom role deleted"))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun CustomRole.toResponse() = mapOf(
        "id" to id.toString(),
        "organizationId" to organizationId.toString(),
        "name" to name,
        "permissions" to permissions,
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

data class CreateCustomRoleRequest(val name: String, val permissions: Map<String, Boolean>)
data class UpdateCustomRoleRequest(val name: String? = null, val permissions: Map<String, Boolean>? = null)
