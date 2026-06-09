package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.TransitionPlatformPostUseCase
import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
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

class PlatformPostTransitionApiTest {

    @Test
    fun `valid transition returns 200`() {
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostId = UUID.randomUUID()
        val postId = UUID.randomUUID()

        val pp = PlatformPost(
            id = platformPostId,
            postId = postId,
            socialAccountId = UUID.randomUUID(),
            platformTitle = null,
            platformCaption = null,
            platformFirstComment = null,
            platformMedia = null,
            platformExtra = null,
            status = PlatformPostStatus.DRAFT,
            platformPostId = "",
            publishError = "",
            publishedAt = null,
            scheduledAt = null,
            retryCount = 0,
            nextRetryAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )

        Mockito.doReturn(pp).`when`(platformPostRepository).findById(platformPostId)
        Mockito.doReturn(emptyList<PlatformPost>()).`when`(platformPostRepository).findByPostId(postId)

        val useCase = TransitionPlatformPostUseCase(platformPostRepository, postRepository)
        val api = PlatformPostTransitionApi(useCase)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val workspaceId = UUID.randomUUID()
            val requestBody = """{"targetStatus":"PENDING_REVIEW"}"""
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8091/api/workspaces/${workspaceId}/posts/${postId}/platform-posts/${platformPostId}/transition"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("PENDING_REVIEW"))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `invalid transition returns 400`() {
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostId = UUID.randomUUID()
        val postId = UUID.randomUUID()

        val pp = PlatformPost(
            id = platformPostId,
            postId = postId,
            socialAccountId = UUID.randomUUID(),
            platformTitle = null,
            platformCaption = null,
            platformFirstComment = null,
            platformMedia = null,
            platformExtra = null,
            status = PlatformPostStatus.PUBLISHED,
            platformPostId = "",
            publishError = "",
            publishedAt = Instant.now(),
            scheduledAt = null,
            retryCount = 0,
            nextRetryAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )

        Mockito.doReturn(pp).`when`(platformPostRepository).findById(platformPostId)

        val useCase = TransitionPlatformPostUseCase(platformPostRepository, postRepository)
        val api = PlatformPostTransitionApi(useCase)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val workspaceId = UUID.randomUUID()
            val requestBody = """{"targetStatus":"DRAFT"}"""
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8091/api/workspaces/${workspaceId}/posts/${postId}/platform-posts/${platformPostId}/transition"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(400, response.statusCode())
            assertTrue(response.body().contains("Invalid status transition"))
        } finally {
            server.stop(0)
        }
    }

    private fun createTestServer(handler: com.sun.net.httpserver.HttpHandler): com.sun.net.httpserver.HttpServer {
        return com.sun.net.httpserver.HttpServer.create(
            java.net.InetSocketAddress("localhost", 8091), 0
        ).apply {
            createContext("/", handler)
            executor = null
        }
    }
}
