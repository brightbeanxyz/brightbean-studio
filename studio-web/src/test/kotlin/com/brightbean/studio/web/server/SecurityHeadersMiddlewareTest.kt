package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpHandler
import com.sun.net.httpserver.HttpServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.net.InetSocketAddress
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

class SecurityHeadersMiddlewareTest {
    private lateinit var server: HttpServer
    private var port: Int = 0
    private val client = HttpClient.newHttpClient()

    @BeforeEach
    fun setUp() {
        val okHandler = HttpHandler { exchange ->
            val response = """{"ok":true}"""
            exchange.responseHeaders.set("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, response.toByteArray().size.toLong())
            exchange.responseBody.use { it.write(response.toByteArray()) }
        }
        val secured = SecurityHeadersMiddleware(okHandler)
        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        server.createContext("/", secured)
        server.executor = null
        server.start()
        port = server.address.port
    }

    @AfterEach
    fun tearDown() { server.stop(0) }

    @Test
    fun `response has security headers`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/test")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertEquals("DENY", response.headers().firstValue("X-Frame-Options").orElse(""))
        assertEquals("nosniff", response.headers().firstValue("X-Content-Type-Options").orElse(""))
        assertTrue(response.headers().firstValue("Strict-Transport-Security").orElse("").contains("max-age=31536000"))
        assertTrue(response.headers().firstValue("Content-Security-Policy").orElse("").contains("default-src"))
        assertEquals("1; mode=block", response.headers().firstValue("X-XSS-Protection").orElse(""))
        assertEquals("strict-origin-when-cross-origin", response.headers().firstValue("Referrer-Policy").orElse(""))
    }
}
