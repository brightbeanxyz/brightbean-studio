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

class RateLimitMiddlewareTest {
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
        val rateLimited = RateLimitMiddleware(okHandler, authLimitPerMinute = 3, apiLimitPerMinute = 100)
        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        server.createContext("/", rateLimited)
        server.executor = null
        server.start()
        port = server.address.port
    }

    @AfterEach
    fun tearDown() { server.stop(0) }

    @Test
    fun `under limit passes through`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/workspaces")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
    }

    @Test
    fun `at auth limit returns 429`() {
        for (i in 1..3) {
            val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/auth/login")).GET().build()
            client.send(request, HttpResponse.BodyHandlers.ofString())
        }
        val fourthRequest = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/auth/login")).GET().build()
        val response = client.send(fourthRequest, HttpResponse.BodyHandlers.ofString())
        assertEquals(429, response.statusCode())
        assertTrue(response.body().contains("Too Many Requests"))
    }

    @Test
    fun `429 response has Retry-After header`() {
        for (i in 1..3) {
            val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/auth/register")).GET().build()
            client.send(request, HttpResponse.BodyHandlers.ofString())
        }
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/auth/register")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(429, response.statusCode())
        assertEquals("60", response.headers().firstValue("Retry-After").orElse(""))
    }
}
