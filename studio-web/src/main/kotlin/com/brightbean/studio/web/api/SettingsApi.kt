package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.SettingsUseCases
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class SettingsApi(
    private val settingsUseCases: SettingsUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/orgs/[^/]+/settings$")) && method == "GET" -> getOrgSettings(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/settings$")) && method == "PUT" -> setOrgSetting(exchange)
            path.matches(Regex("^/api/orgs/[^/]+/settings/[^/]+$")) && method == "GET" -> getOrgSetting(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/settings$")) && method == "GET" -> getWorkspaceSettings(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/settings$")) && method == "PUT" -> setWorkspaceSetting(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/settings/[^/]+$")) && method == "GET" -> getWorkspaceSetting(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun getOrgSettings(exchange: HttpExchange) {
        try {
            val orgId = extractOrgId(exchange)
            sendJson(exchange, 200, settingsUseCases.getOrgSettings(orgId))
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun getOrgSetting(exchange: HttpExchange) {
        try {
            val orgId = extractOrgId(exchange)
            val key = exchange.requestURI.path.split("/").last()
            val setting = settingsUseCases.getOrgSetting(orgId, key)
            if (setting != null) sendJson(exchange, 200, setting) else sendJson(exchange, 200, null)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun setOrgSetting(exchange: HttpExchange) {
        try {
            val orgId = extractOrgId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val setting = settingsUseCases.setOrgSetting(orgId, req["key"] as String, req["value"] as String)
            sendJson(exchange, 200, setting)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to set org setting")
        }
    }

    private fun getWorkspaceSettings(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            sendJson(exchange, 200, settingsUseCases.getWorkspaceSettings(workspaceId))
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun getWorkspaceSetting(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val key = exchange.requestURI.path.split("/").last()
            val setting = settingsUseCases.getWorkspaceSetting(workspaceId, key)
            if (setting != null) sendJson(exchange, 200, setting) else sendJson(exchange, 200, null)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun setWorkspaceSetting(exchange: HttpExchange) {
        try {
            val workspaceId = extractWorkspaceId(exchange)
            val body = InputStreamReader(exchange.requestBody).readText()
            val req = gson.fromJson(body, Map::class.java)
            val setting = settingsUseCases.setWorkspaceSetting(workspaceId, req["key"] as String, req["value"] as? String)
            sendJson(exchange, 200, setting)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to set workspace setting")
        }
    }

    private fun extractOrgId(exchange: HttpExchange): UUID = UUID.fromString(exchange.requestURI.path.split("/")[3])
    private fun extractWorkspaceId(exchange: HttpExchange): UUID = UUID.fromString(exchange.requestURI.path.split("/")[3])

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any?) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(error = when (statusCode) { 400 -> "Bad Request"; 404 -> "Not Found"; 500 -> "Internal Server Error"; else -> "Error" }, message = message, statusCode = statusCode)
        sendJson(exchange, statusCode, error)
    }
}
