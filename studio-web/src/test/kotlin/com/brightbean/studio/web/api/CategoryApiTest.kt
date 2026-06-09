package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.ContentCategoryUseCases
import com.brightbean.studio.domain.model.ContentCategory
import com.brightbean.studio.domain.repository.ContentCategoryRepository
import com.brightbean.studio.web.server.Middleware
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.mockito.Mockito
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Instant
import java.util.UUID

class CategoryApiTest {

    @Test
    fun `list categories returns 200 with empty list`() {
        val repository = Mockito.mock(ContentCategoryRepository::class.java)
        val workspaceId = UUID.randomUUID()

        Mockito.`when`(repository.findByWorkspaceId(workspaceId)).thenReturn(emptyList())

        val useCases = ContentCategoryUseCases(repository)
        val api = CategoryApi(useCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8088/api/workspaces/${workspaceId}/categories"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertEquals("[]", response.body())
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list categories returns 200 with items`() {
        val repository = Mockito.mock(ContentCategoryRepository::class.java)
        val workspaceId = UUID.randomUUID()
        val now = Instant.now()

        val category = ContentCategory(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = "Marketing",
            color = "#FF0000",
            position = 0,
            createdAt = now,
            updatedAt = now,
        )

        Mockito.`when`(repository.findByWorkspaceId(workspaceId)).thenReturn(listOf(category))

        val useCases = ContentCategoryUseCases(repository)
        val api = CategoryApi(useCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8088/api/workspaces/${workspaceId}/categories"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"name\":\"Marketing\""))
            assertTrue(response.body().contains("\"color\":\"#FF0000\""))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `delete category returns 200`() {
        val repository = Mockito.mock(ContentCategoryRepository::class.java)
        val categoryId = UUID.randomUUID()

        Mockito.doNothing().`when`(repository).delete(categoryId)

        val useCases = ContentCategoryUseCases(repository)
        val api = CategoryApi(useCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8088/api/workspaces/${UUID.randomUUID()}/categories/${categoryId}"))
                .DELETE()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"deleted\":true"))
        } finally {
            server.stop(0)
        }
    }

    private fun createTestServer(handler: com.sun.net.httpserver.HttpHandler): com.sun.net.httpserver.HttpServer {
        return com.sun.net.httpserver.HttpServer.create(
            java.net.InetSocketAddress("localhost", 8088), 0
        ).apply {
            createContext("/", handler)
            executor = null
        }
    }
}
