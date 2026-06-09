package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler

class SecurityHeadersMiddleware(
    private val next: HttpHandler,
    private val cspPolicy: String = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; connect-src 'self'",
) : HttpHandler {
    override fun handle(exchange: HttpExchange) {
        exchange.responseHeaders.apply {
            set("Content-Security-Policy", cspPolicy)
            set("X-Frame-Options", "DENY")
            set("X-Content-Type-Options", "nosniff")
            set("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
            set("X-XSS-Protection", "1; mode=block")
            set("Referrer-Policy", "strict-origin-when-cross-origin")
        }
        next.handle(exchange)
    }
}
