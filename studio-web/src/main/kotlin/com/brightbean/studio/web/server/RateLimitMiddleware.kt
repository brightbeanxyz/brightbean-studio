package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import java.time.Instant
import java.util.concurrent.ConcurrentHashMap

class RateLimitMiddleware(
    private val next: HttpHandler,
    private val authLimitPerMinute: Int = 10,
    private val apiLimitPerMinute: Int = 100,
) : HttpHandler {
    private val requestLog = ConcurrentHashMap<String, MutableList<Instant>>()

    override fun handle(exchange: HttpExchange) {
        val clientIp = exchange.remoteAddress.address.hostAddress
        val path = exchange.requestURI.path
        val isAuthEndpoint = path.contains("/api/auth/login") || path.contains("/api/auth/register")
        val limit = if (isAuthEndpoint) authLimitPerMinute else apiLimitPerMinute

        val key = "$clientIp:${if (isAuthEndpoint) "auth" else "api"}"
        val now = Instant.now()
        val windowStart = now.minusSeconds(60)

        val timestamps = requestLog.getOrPut(key) { mutableListOf() }
        synchronized(timestamps) {
            timestamps.removeAll { it.isBefore(windowStart) }
            if (timestamps.size >= limit) {
                val response = """{"error":"Too Many Requests","statusCode":429}"""
                exchange.responseHeaders.set("Content-Type", "application/json")
                exchange.responseHeaders.set("Retry-After", "60")
                exchange.sendResponseHeaders(429, response.toByteArray().size.toLong())
                exchange.responseBody.use { it.write(response.toByteArray()) }
                return
            }
            timestamps.add(now)
        }
        next.handle(exchange)
    }
}
