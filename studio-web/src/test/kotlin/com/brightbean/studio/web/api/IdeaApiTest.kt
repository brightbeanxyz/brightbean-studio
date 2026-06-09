package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.IdeaGroupUseCases
import com.brightbean.studio.application.usecase.IdeaUseCases
import com.brightbean.studio.domain.model.Idea
import com.brightbean.studio.domain.model.IdeaGroup
import com.brightbean.studio.domain.model.IdeaStatus
import com.brightbean.studio.domain.repository.IdeaGroupRepository
import com.brightbean.studio.domain.repository.IdeaMediaRepository
import com.brightbean.studio.domain.repository.IdeaRepository
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostMediaRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
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

class IdeaApiTest {

    @Test
    fun `list ideas returns 200 with empty list`() {
        val ideaRepository = Mockito.mock(IdeaRepository::class.java)
        val ideaMediaRepository = Mockito.mock(IdeaMediaRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val postMediaRepository = Mockito.mock(PostMediaRepository::class.java)
        val socialAccountRepository = Mockito.mock(SocialAccountRepository::class.java)
        val workspaceId = UUID.randomUUID()

        Mockito.`when`(ideaRepository.findByWorkspaceId(workspaceId)).thenReturn(emptyList())

        val ideaUseCases = IdeaUseCases(ideaRepository, ideaMediaRepository, postRepository, platformPostRepository, postMediaRepository, socialAccountRepository)
        val ideaGroupUseCases = IdeaGroupUseCases(Mockito.mock(IdeaGroupRepository::class.java))
        val api = IdeaApi(ideaUseCases, ideaGroupUseCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8089/api/workspaces/${workspaceId}/ideas"))
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
    fun `list ideas returns 200 with items`() {
        val ideaRepository = Mockito.mock(IdeaRepository::class.java)
        val ideaMediaRepository = Mockito.mock(IdeaMediaRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val postMediaRepository = Mockito.mock(PostMediaRepository::class.java)
        val socialAccountRepository = Mockito.mock(SocialAccountRepository::class.java)
        val workspaceId = UUID.randomUUID()
        val now = Instant.now()

        val idea = Idea(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = null,
            title = "My idea",
            description = "A great idea",
            tags = listOf("marketing"),
            mediaAssetId = null,
            status = IdeaStatus.UNASSIGNED,
            groupId = null,
            position = 0,
            postId = null,
            createdAt = now,
            updatedAt = now,
        )

        Mockito.`when`(ideaRepository.findByWorkspaceId(workspaceId)).thenReturn(listOf(idea))

        val ideaUseCases = IdeaUseCases(ideaRepository, ideaMediaRepository, postRepository, platformPostRepository, postMediaRepository, socialAccountRepository)
        val ideaGroupUseCases = IdeaGroupUseCases(Mockito.mock(IdeaGroupRepository::class.java))
        val api = IdeaApi(ideaUseCases, ideaGroupUseCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8089/api/workspaces/${workspaceId}/ideas"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"title\":\"My idea\""))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list idea groups returns 200`() {
        val ideaRepository = Mockito.mock(IdeaRepository::class.java)
        val ideaMediaRepository = Mockito.mock(IdeaMediaRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val postMediaRepository = Mockito.mock(PostMediaRepository::class.java)
        val socialAccountRepository = Mockito.mock(SocialAccountRepository::class.java)
        val ideaGroupRepository = Mockito.mock(IdeaGroupRepository::class.java)
        val workspaceId = UUID.randomUUID()

        Mockito.`when`(ideaGroupRepository.findByWorkspaceId(workspaceId)).thenReturn(emptyList())

        val ideaUseCases = IdeaUseCases(ideaRepository, ideaMediaRepository, postRepository, platformPostRepository, postMediaRepository, socialAccountRepository)
        val ideaGroupUseCases = IdeaGroupUseCases(ideaGroupRepository)
        val api = IdeaApi(ideaUseCases, ideaGroupUseCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8089/api/workspaces/${workspaceId}/idea-groups"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertEquals("[]", response.body())
        } finally {
            server.stop(0)
        }
    }

    private fun createTestServer(handler: com.sun.net.httpserver.HttpHandler): com.sun.net.httpserver.HttpServer {
        return com.sun.net.httpserver.HttpServer.create(
            java.net.InetSocketAddress("localhost", 8089), 0
        ).apply {
            createContext("/", handler)
            executor = null
        }
    }
}
