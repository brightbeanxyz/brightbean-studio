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

class RouterTest {
    private lateinit var server: HttpServer
    private var port: Int = 0
    private val client = HttpClient.newHttpClient()

    @BeforeEach
    fun setUp() {
        val healthHandler = HttpHandler { exchange ->
            val response = """{"status":"UP"}"""
            exchange.responseHeaders.set("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, response.toByteArray().size.toLong())
            exchange.responseBody.use { it.write(response.toByteArray()) }
        }
        val apiHandler = HttpHandler { exchange ->
            val response = """{"api":true}"""
            exchange.responseHeaders.set("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, response.toByteArray().size.toLong())
            exchange.responseBody.use { it.write(response.toByteArray()) }
        }
        val router = Router(
            routes = mapOf(
                "/health" to healthHandler,
                "/api" to apiHandler,
            )
        )
        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        server.createContext("/", router)
        server.executor = null
        server.start()
        port = server.address.port
    }

    @AfterEach
    fun tearDown() { server.stop(0) }

    @Test
    fun `routes to health handler`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/health")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertTrue(response.body().contains("UP"))
    }

    @Test
    fun `routes to api handler`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/workspaces/123")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertTrue(response.body().contains("api"))
    }

    @Test
    fun `returns 404 for unknown path`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/unknown")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(404, response.statusCode())
        assertTrue(response.body().contains("Not Found"))
    }
}
