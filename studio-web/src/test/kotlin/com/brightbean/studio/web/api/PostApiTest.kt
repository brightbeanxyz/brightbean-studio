package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.CreatePostUseCase
import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.application.usecase.SchedulePostUseCase
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.web.server.Middleware
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.Mockito
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Instant
import java.util.UUID

class PostApiTest {

    private val workspaceId = UUID.randomUUID()
    private val authorId = UUID.randomUUID()

    @Test
    fun `unknown path returns 404`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val createPostUseCase = Mockito.mock(CreatePostUseCase::class.java)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)
        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)

        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/unknown"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(404, response.statusCode())
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list posts returns 200 with empty list`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val createPostUseCase = Mockito.mock(CreatePostUseCase::class.java)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)
        
        Mockito.doReturn(emptyList<Post>()).`when`(postRepository).findByWorkspaceId(workspaceId)

        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)
        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/workspaces/${workspaceId}/posts"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"items\":[]"))
            assertTrue(response.body().contains("\"totalCount\":0"))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list posts returns paginated response with posts`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val createPostUseCase = Mockito.mock(CreatePostUseCase::class.java)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)

        val post1 = Post(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = authorId,
            content = "Test content 1",
            platforms = listOf(PlatformType.FACEBOOK),
            categoryId = null,
            tags = emptyList(),
            status = PostStatus.DRAFT,
            scheduledAt = null,
            publishedAt = null,
            mediaIds = emptyList(),
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        val post2 = Post(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = authorId,
            content = "Test content 2",
            platforms = listOf(PlatformType.INSTAGRAM),
            categoryId = null,
            tags = emptyList(),
            status = PostStatus.SCHEDULED,
            scheduledAt = Instant.now(),
            publishedAt = null,
            mediaIds = emptyList(),
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )

        Mockito.doReturn(listOf(post1, post2)).`when`(postRepository).findByWorkspaceId(workspaceId)

        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)
        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/workspaces/${workspaceId}/posts"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"items\""))
            assertTrue(response.body().contains("\"totalCount\":2"))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list posts with status filter`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val createPostUseCase = Mockito.mock(CreatePostUseCase::class.java)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)

        val draftPost = Post(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            authorId = authorId,
            content = "Draft content",
            platforms = listOf(PlatformType.FACEBOOK),
            categoryId = null,
            tags = emptyList(),
            status = PostStatus.DRAFT,
            scheduledAt = null,
            publishedAt = null,
            mediaIds = emptyList(),
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )

        Mockito.doReturn(listOf(draftPost)).`when`(postRepository).findByWorkspaceId(workspaceId)

        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)
        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/workspaces/${workspaceId}/posts?status=DRAFT"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"status\":\"DRAFT\""))
        } finally {
            server.stop(0)
        }
    }

    private fun createTestServer(handler: com.sun.net.httpserver.HttpHandler): com.sun.net.httpserver.HttpServer {
        return com.sun.net.httpserver.HttpServer.create(
            java.net.InetSocketAddress("localhost", 8087), 0
        ).apply {
            createContext("/", handler)
            executor = null
        }
    }
}
