package com.brightbean.studio.web.api

import com.brightbean.studio.application.auth.WorkspacePermissionKeys
import com.brightbean.studio.application.usecase.ConnectSocialAccountUseCase
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.web.api.dto.ConnectSocialAccountRequest
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.brightbean.studio.web.api.dto.SocialAccountResponse
import com.brightbean.studio.web.api.dto.toResponse
import com.brightbean.studio.web.server.PermissionChecks
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.util.UUID

class SocialAccountApi(
    private val connectSocialAccountUseCase: ConnectSocialAccountUseCase,
    private val socialAccountRepository: SocialAccountRepository,
) : HttpHandler {

    private val gson = com.google.gson.Gson()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/social-accounts$")) && method == "GET" -> listAccounts(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/social-accounts/connect$")) && method == "POST" -> connectAccount(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/social-accounts/[^/]+$")) && method == "DELETE" -> disconnectAccount(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listAccounts(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[4])

            val accounts = socialAccountRepository.findByWorkspaceId(workspaceId)
            val response = accounts.map { it.toResponse() }

            sendJson(exchange, 200, response)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun connectAccount(exchange: HttpExchange) {
        if (!PermissionChecks.hasPermission(exchange, WorkspacePermissionKeys.MANAGE_SOCIAL_ACCOUNTS)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[4])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, ConnectSocialAccountRequest::class.java)

            val account = connectSocialAccountUseCase.execute(
                workspaceId = workspaceId,
                platformType = request.platformType,
                authorizationCode = request.authorizationCode,
            )

            sendJson(exchange, 201, account.toResponse())
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to connect social account")
        }
    }

    private fun disconnectAccount(exchange: HttpExchange) {
        if (!PermissionChecks.hasPermission(exchange, WorkspacePermissionKeys.MANAGE_SOCIAL_ACCOUNTS)) {
            sendError(exchange, 403, "Forbidden"); return
        }
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[4])
            val accountId = UUID.fromString(pathParts[6])

            val account = socialAccountRepository.findById(accountId)
            if (account == null || account.workspaceId != workspaceId) {
                sendError(exchange, 404, "Social account not found")
                return
            }

            socialAccountRepository.delete(accountId)
            sendJson(exchange, 204, "")
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
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
}
