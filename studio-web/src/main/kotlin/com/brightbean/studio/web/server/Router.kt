package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler

class Router(
    private val routes: Map<String, HttpHandler>,
    private val notFoundHandler: HttpHandler = NotFoundHandler(),
) : HttpHandler {
    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val matchedRoute = routes.entries
            .filter { path.startsWith(it.key) }
            .maxByOrNull { it.key.length }
        matchedRoute?.value?.handle(exchange) ?: notFoundHandler.handle(exchange)
    }
}

class NotFoundHandler : HttpHandler {
    override fun handle(exchange: HttpExchange) {
        val response = """{"error":"Not Found","statusCode":404}"""
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(404, response.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(response.toByteArray()) }
    }
}
