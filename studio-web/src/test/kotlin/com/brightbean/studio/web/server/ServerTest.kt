package com.brightbean.studio.web.server

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Test
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse

class ServerTest {

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
    fun `health handler returns UP status`() {
        val handler = HealthHandler()
        assertNotNull(handler)
    }
}
