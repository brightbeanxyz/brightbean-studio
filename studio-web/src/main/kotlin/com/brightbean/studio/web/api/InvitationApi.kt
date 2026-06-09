package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.*
import com.brightbean.studio.domain.model.Invitation
import com.brightbean.studio.domain.model.InvitationStatus
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.WorkspaceRole
import com.brightbean.studio.domain.repository.InvitationRepository
import com.brightbean.studio.web.server.PermissionChecks
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class InvitationApi(
    private val createInvitationUseCase: CreateInvitationUseCase,
    private val acceptInvitationUseCase: AcceptInvitationUseCase,
    private val resendInvitationUseCase: ResendInvitationUseCase,
    private val revokeInvitationUseCase: RevokeInvitationUseCase,
    private val invitationRepository: InvitationRepository,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/invitations/[^/]+/resend$")) && method == "POST" -> resendInvitation(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/invitations/[^/]+/revoke$")) && method == "POST" -> revokeInvitation(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/invitations$")) && method == "GET" -> listInvitations(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/invitations$")) && method == "POST" -> createInvitation(exchange)
            path.matches(Regex("^/api/invitations/[^/]+/accept$")) && method == "POST" -> acceptInvitation(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listInvitations(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.MEMBER)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val invitations = invitationRepository.findByOrganizationId(orgId)
                .filter { it.status == InvitationStatus.PENDING }
            sendJson(exchange, 200, invitations.map { it.toResponse() })
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createInvitation(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val orgId = UUID.fromString(pathParts[3])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateInvitationRequest::class.java)

            val assignments = request.workspaceAssignments.map {
                WorkspaceAssignment(UUID.fromString(it.workspaceId), WorkspaceRole.valueOf(it.role))
            }
            val result = createInvitationUseCase.execute(orgId, request.email, OrgRole.valueOf(request.orgRole), assignments, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 422, result.exceptionOrNull()?.message ?: "Failed to create invitation"); return
            }
            sendJson(exchange, 201, result.getOrNull()!!.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create invitation")
        }
    }

    private fun resendInvitation(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val invitationId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val result = resendInvitationUseCase.execute(invitationId, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 400, result.exceptionOrNull()?.message ?: "Failed to resend invitation"); return
            }
            sendJson(exchange, 200, result.getOrNull()!!.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to resend invitation")
        }
    }

    private fun revokeInvitation(exchange: HttpExchange) {
        if (!PermissionChecks.hasOrgRole(exchange, OrgRole.ADMIN)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val invitationId = UUID.fromString(pathParts[5])
            val context = PermissionChecks.getRbacContext(exchange)!!
            val result = revokeInvitationUseCase.execute(invitationId, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 400, result.exceptionOrNull()?.message ?: "Failed to revoke invitation"); return
            }
            sendJson(exchange, 200, result.getOrNull()!!.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to revoke invitation")
        }
    }

    private fun acceptInvitation(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val token = pathParts[3]
            val context = PermissionChecks.getRbacContext(exchange) ?: run {
                sendError(exchange, 401, "Authentication required"); return
            }
            val result = acceptInvitationUseCase.execute(token, context.user.id)
            if (result.isFailure) {
                sendError(exchange, 400, result.exceptionOrNull()?.message ?: "Failed to accept invitation"); return
            }
            sendJson(exchange, 200, mapOf("orgMembershipId" to result.getOrNull()!!.id.toString()))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to accept invitation")
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

    private fun Invitation.toResponse() = mapOf(
        "id" to id.toString(),
        "organizationId" to organizationId.toString(),
        "email" to email,
        "orgRole" to orgRole.name,
        "workspaceAssignments" to workspaceAssignments,
        "invitedBy" to invitedBy?.toString(),
        "token" to token,
        "expiresAt" to expiresAt.toString(),
        "acceptedAt" to acceptedAt?.toString(),
        "status" to status.name,
        "createdAt" to createdAt.toString(),
    )
}

data class CreateInvitationRequest(
    val email: String,
    val orgRole: String,
    val workspaceAssignments: List<WorkspaceAssignmentRequest>,
)

data class WorkspaceAssignmentRequest(
    val workspaceId: String,
    val role: String,
)
