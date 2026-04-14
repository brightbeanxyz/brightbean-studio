package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.CreatePostUseCase
import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.application.usecase.SchedulePostUseCase
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.Tag
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

    @Test
    fun `create post returns 201 with created post`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val approvalRequestRepository = Mockito.mock(com.brightbean.studio.domain.repository.ApprovalRequestRepository::class.java)
        val createPostUseCase = com.brightbean.studio.application.usecase.CreatePostUseCase(postRepository, approvalRequestRepository)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)

        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)
        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val requestBody = """
                {
                    "content": "New post content",
                    "platforms": ["FACEBOOK"],
                    "requiresApproval": false,
                    "mediaIds": []
                }
            """.trimIndent()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/workspaces/${workspaceId}/posts"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(201, response.statusCode())
            assertTrue(response.body().contains("\"content\":\"New post content\""))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `publish post returns 200 with published post`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val createPostUseCase = Mockito.mock(CreatePostUseCase::class.java)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)

        val postId = UUID.randomUUID()
        val publishedPost = Post(
            id = postId,
            workspaceId = workspaceId,
            authorId = authorId,
            content = "Published content",
            platforms = listOf(PlatformType.FACEBOOK),
            categoryId = null,
            tags = emptyList(),
            status = PostStatus.PUBLISHED,
            scheduledAt = null,
            publishedAt = Instant.now(),
            mediaIds = emptyList(),
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )

        Mockito.doReturn(publishedPost).`when`(publishPostUseCase).execute(postId)

        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)
        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/posts/${postId}/publish"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.noBody())
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"status\":\"PUBLISHED\""))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `schedule post returns 200 with queue info`() {
        val postRepository = Mockito.mock(PostRepository::class.java)
        val createPostUseCase = Mockito.mock(CreatePostUseCase::class.java)
        val schedulePostUseCase = Mockito.mock(SchedulePostUseCase::class.java)
        val publishPostUseCase = Mockito.mock(PublishPostUseCase::class.java)

        val postId = UUID.randomUUID()
        val queueId = UUID.randomUUID()
        val scheduledFor = Instant.parse("2025-12-01T10:00:00Z")
        val scheduledPost = Post(
            id = postId,
            workspaceId = workspaceId,
            authorId = authorId,
            content = "Scheduled content",
            platforms = listOf(PlatformType.FACEBOOK),
            categoryId = null,
            tags = emptyList(),
            status = PostStatus.SCHEDULED,
            scheduledAt = scheduledFor,
            publishedAt = null,
            mediaIds = emptyList(),
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        val queue = com.brightbean.studio.domain.model.PublishingQueue(
            id = queueId,
            workspaceId = workspaceId,
            postId = postId,
            scheduledFor = scheduledFor,
            attempts = 0,
            lastAttemptAt = null,
            status = com.brightbean.studio.domain.model.QueueStatus.PENDING,
            errorMessage = null,
        )

        Mockito.doReturn(queue).`when`(schedulePostUseCase).execute(postId, scheduledFor)
        Mockito.doReturn(scheduledPost).`when`(postRepository).findById(postId)

        val postApi = PostApi(createPostUseCase, schedulePostUseCase, publishPostUseCase, postRepository)
        val handler = Middleware.corsMiddleware(listOf("*"), postApi)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val requestBody = """
                {
                    "scheduledFor": "2025-12-01T10:00:00Z"
                }
            """.trimIndent()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8087/api/posts/${postId}/schedule"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"queueId\":\"$queueId\""))
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
