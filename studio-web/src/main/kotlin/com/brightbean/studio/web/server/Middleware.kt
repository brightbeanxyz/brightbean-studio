package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpHandler
import com.sun.net.httpserver.HttpExchange

object Middleware {
    fun defaultCorsOrigins(): List<String> = listOf("*")

    fun corsMiddleware(origins: List<String>, next: HttpHandler): HttpHandler {
        return HttpHandler { exchange ->
            exchange.responseHeaders.set("Access-Control-Allow-Origin", origins.joinToString(","))
            exchange.responseHeaders.set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            exchange.responseHeaders.set("Access-Control-Allow-Headers", "Content-Type, Authorization")
            if (exchange.requestMethod == "OPTIONS") {
                exchange.sendResponseHeaders(204, -1)
                return@HttpHandler
            }
            next.handle(exchange)
        }
    }
}
