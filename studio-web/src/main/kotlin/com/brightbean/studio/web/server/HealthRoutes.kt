package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpServer
import com.sun.net.httpserver.HttpHandler
import com.sun.net.httpserver.HttpExchange
import java.io.OutputStream
import java.net.URI

class HealthHandler : HttpHandler {
    override fun handle(exchange: HttpExchange) {
        when (exchange.requestMethod) {
            "GET" -> {
                if (exchange.requestURI.path == "/health" || exchange.requestURI.path == "/") {
                    val response = """{"status":"UP"}"""
                    exchange.responseHeaders.set("Content-Type", "application/json")
                    exchange.sendResponseHeaders(200, response.toByteArray().size.toLong())
                    exchange.responseBody.use { os ->
                        os.write(response.toByteArray())
                    }
                } else {
                    exchange.sendResponseHeaders(404, -1)
                }
            }
            else -> exchange.sendResponseHeaders(405, -1)
        }
    }
}
