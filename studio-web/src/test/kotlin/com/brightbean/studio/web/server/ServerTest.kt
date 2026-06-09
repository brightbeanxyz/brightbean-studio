package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.net.InetSocketAddress
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

class ServerTest {

    private lateinit var server: HttpServer
    private var port: Int = 0

    @BeforeEach
    fun setUp() {
        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        val healthHandler = Middleware.corsMiddleware(listOf("*"), HealthHandler())
        server.createContext("/health", healthHandler)
        server.createContext("/", healthHandler)
        server.executor = null
        server.start()
        port = server.address.port
    }

    @AfterEach
    fun tearDown() {
        server.stop(0)
    }

    @Test
    fun `server config has default values`() {
        val config = ServerConfig()
        assertEquals("0.0.0.0", config.host)
        assertEquals(8080, config.port)
        assertEquals(listOf("*"), config.corsOrigins)
    }

    @Test
    fun `server config can be customized`() {
        val config = ServerConfig(
            host = "localhost",
            port = 3000,
            corsOrigins = listOf("https://example.com"),
        )
        assertEquals("localhost", config.host)
        assertEquals(3000, config.port)
        assertEquals(listOf("https://example.com"), config.corsOrigins)
    }

    @Test
    fun `middleware default cors returns star`() {
        val cors = Middleware.defaultCorsOrigins()
        assertEquals(listOf("*"), cors)
    }

    @Test
    fun `health endpoint returns UP status`() {
        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/health"))
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertEquals("""{"status":"UP"}""", response.body())
    }
}
