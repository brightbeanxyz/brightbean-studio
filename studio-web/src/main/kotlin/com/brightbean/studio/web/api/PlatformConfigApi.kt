package com.brightbean.studio.web.api

import com.brightbean.studio.application.auth.PlatformConfig
import com.brightbean.studio.domain.model.PlatformType
import com.google.gson.Gson
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler

class PlatformConfigApi : HttpHandler {

    private val gson = Gson()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/platforms/[^/]+$")) && method == "GET" -> getPlatformConfig(exchange)
            path.matches(Regex("^/api/platforms$")) && method == "GET" -> listPlatforms(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listPlatforms(exchange: HttpExchange) {
        val platforms = PlatformType.values().map { pt ->
            mapOf(
                "name" to pt.name,
                "charLimit" to PlatformConfig.getCharLimit(pt.name),
                "fieldConfig" to PlatformConfig.getFieldConfig(pt.name),
            )
        }
        sendJson(exchange, 200, platforms)
    }

    private fun getPlatformConfig(exchange: HttpExchange) {
        val pathParts = exchange.requestURI.path.split("/")
        val platform = pathParts[3]
        try {
            PlatformType.valueOf(platform)
        } catch (_: Exception) {
            sendError(exchange, 404, "Platform not found: $platform"); return
        }
        sendJson(exchange, 200, mapOf(
            "name" to platform,
            "charLimit" to PlatformConfig.getCharLimit(platform),
            "fieldConfig" to PlatformConfig.getFieldConfig(platform),
        ))
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
