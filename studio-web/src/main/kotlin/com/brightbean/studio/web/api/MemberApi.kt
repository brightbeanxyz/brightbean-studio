package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.*
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.WorkspaceRole
import com.brightbean.studio.domain.repository.OrgMembershipRepository
import com.brightbean.studio.domain.repository.WorkspaceMembershipRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import com.brightbean.studio.web.server.PermissionChecks
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class MemberApi(
    private val updateMemberOrgRoleUseCase: UpdateMemberOrgRoleUseCase,
    private val removeMemberUseCase: RemoveMemberUseCase,
    private val updateWorkspaceAssignmentsUseCase: UpdateWorkspaceAssignmentsUseCase,
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val workspaceRepository: WorkspaceRepository,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/members/[^/]+/workspaces$")) && method == "GET" -> listWorkspaceAssignments(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/members/[^/]+/workspaces$")) && method == "PUT" -> updateWorkspaceAssignments(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/members/[^/]+/role$")) && method == "PUT" -> updateMemberRole(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/members/[^/]+/remove$")) && method == "POST" -> removeMember(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/members$")) && method == "GET" -> listMembers(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listMembers(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.MEMBER)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val members = orgMembershipRepository.findByOrganizationId(orgId)
            sendJson(exchange, 200, members.map { mapOf(
                "id" to it.id.toString(),
                "userId" to it.userId.toString(),
                "organizationId" to it.organizationId.toString(),
                "orgRole" to it.orgRole.name,
                "invitedAt" to it.invitedAt.toString(),
                "acceptedAt" to it.acceptedAt?.toString(),
            ) })
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun updateMemberRole(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val membershipId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateRoleRequest::class.java)
            val result = updateMemberOrgRoleUseCase.execute(orgId, membershipId, OrgRole.valueOf(request.orgRole), context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            val m = result.getOrNull()!!
            sendJson(exchange, 200, mapOf("id" to m.id.toString(), "orgRole" to m.orgRole.name))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun removeMember(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val membershipId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val result = removeMemberUseCase.execute(orgId, membershipId, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            sendJson(exchange, 200, mapOf("message" to "Member removed"))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

    private fun listWorkspaceAssignments(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val membershipId = UUID.fromString(pathParts[5])
            val membership = orgMembershipRepository.findById(membershipId)
                ?: run { sendError(exchange, 404, "Membership not found"); return }
            val orgWorkspaces = workspaceRepository.findByOrganizationId(orgId)
            val assignments = workspaceMembershipRepository.findByUserId(membership.userId)
                .filter { orgWorkspaces.any { ws -> ws.id == it.workspaceId } }
            sendJson(exchange, 200, assignments.map { mapOf(
                "id" to it.id.toString(),
                "workspaceId" to it.workspaceId.toString(),
                "workspaceRole" to it.workspaceRole.name,
            ) })
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun updateWorkspaceAssignments(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val membershipId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val membership = orgMembershipRepository.findById(membershipId)
                ?: run { sendError(exchange, 404, "Membership not found"); return }
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateWorkspaceAssignmentsRequest::class.java)
            val assignments = request.assignments.map {
                WorkspaceAssignment(UUID.fromString(it.workspaceId), WorkspaceRole.valueOf(it.role))
            }
            val result = updateWorkspaceAssignmentsUseCase.execute(orgId, membership.userId, assignments, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed"); return
            }
            sendJson(exchange, 200, result.getOrNull()!!.map { mapOf(
                "workspaceId" to it.workspaceId.toString(),
                "workspaceRole" to it.workspaceRole.name,
            ) })
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed")
        }
    }

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

data class UpdateRoleRequest(val orgRole: String)
data class UpdateWorkspaceAssignmentsRequest(val assignments: List<WorkspaceAssignmentRequest>)
