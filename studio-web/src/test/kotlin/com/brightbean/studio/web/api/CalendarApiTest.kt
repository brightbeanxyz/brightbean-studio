package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.CustomCalendarEventUseCases
import com.brightbean.studio.application.usecase.PostingSlotUseCases
import com.brightbean.studio.application.usecase.QueueUseCases
import com.brightbean.studio.application.usecase.ReschedulePostUseCase
import com.brightbean.studio.domain.model.CustomCalendarEvent
import com.brightbean.studio.domain.model.Queue
import com.brightbean.studio.domain.repository.CustomCalendarEventRepository
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.PostingSlotRepository
import com.brightbean.studio.domain.repository.QueueEntryRepository
import com.brightbean.studio.domain.repository.QueueRepository
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
import java.time.LocalDate
import java.util.UUID

class CalendarApiTest {

    @Test
    fun `list events returns 200 with empty list`() {
        val eventRepository = Mockito.mock(CustomCalendarEventRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val queueRepository = Mockito.mock(QueueRepository::class.java)
        val queueEntryRepository = Mockito.mock(QueueEntryRepository::class.java)
        val postingSlotRepository = Mockito.mock(PostingSlotRepository::class.java)
        val workspaceId = UUID.randomUUID()

        Mockito.`when`(eventRepository.findByWorkspaceId(workspaceId)).thenReturn(emptyList())

        val eventUseCases = CustomCalendarEventUseCases(eventRepository)
        val rescheduleUseCase = ReschedulePostUseCase(postRepository, platformPostRepository)
        val queueUseCases = QueueUseCases(queueRepository, queueEntryRepository, postingSlotRepository, postRepository, platformPostRepository)
        val slotUseCases = PostingSlotUseCases(postingSlotRepository)

        val api = CalendarApi(eventUseCases, rescheduleUseCase, queueUseCases, slotUseCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8090/api/workspaces/${workspaceId}/calendar/events"))
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
    fun `list events returns 200 with items`() {
        val eventRepository = Mockito.mock(CustomCalendarEventRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val queueRepository = Mockito.mock(QueueRepository::class.java)
        val queueEntryRepository = Mockito.mock(QueueEntryRepository::class.java)
        val postingSlotRepository = Mockito.mock(PostingSlotRepository::class.java)
        val workspaceId = UUID.randomUUID()
        val now = Instant.now()

        val event = CustomCalendarEvent(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            title = "Team meeting",
            description = "Weekly sync",
            startDate = LocalDate.of(2025, 12, 1),
            endDate = LocalDate.of(2025, 12, 1),
            color = "#4285F4",
            createdBy = null,
            createdAt = now,
            updatedAt = now,
        )

        Mockito.`when`(eventRepository.findByWorkspaceId(workspaceId)).thenReturn(listOf(event))

        val eventUseCases = CustomCalendarEventUseCases(eventRepository)
        val rescheduleUseCase = ReschedulePostUseCase(postRepository, platformPostRepository)
        val queueUseCases = QueueUseCases(queueRepository, queueEntryRepository, postingSlotRepository, postRepository, platformPostRepository)
        val slotUseCases = PostingSlotUseCases(postingSlotRepository)

        val api = CalendarApi(eventUseCases, rescheduleUseCase, queueUseCases, slotUseCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8090/api/workspaces/${workspaceId}/calendar/events"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("\"title\":\"Team meeting\""))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list queues returns 200`() {
        val eventRepository = Mockito.mock(CustomCalendarEventRepository::class.java)
        val postRepository = Mockito.mock(PostRepository::class.java)
        val platformPostRepository = Mockito.mock(PlatformPostRepository::class.java)
        val queueRepository = Mockito.mock(QueueRepository::class.java)
        val queueEntryRepository = Mockito.mock(QueueEntryRepository::class.java)
        val postingSlotRepository = Mockito.mock(PostingSlotRepository::class.java)
        val workspaceId = UUID.randomUUID()

        Mockito.`when`(queueRepository.findByWorkspaceId(workspaceId)).thenReturn(emptyList())

        val eventUseCases = CustomCalendarEventUseCases(eventRepository)
        val rescheduleUseCase = ReschedulePostUseCase(postRepository, platformPostRepository)
        val queueUseCases = QueueUseCases(queueRepository, queueEntryRepository, postingSlotRepository, postRepository, platformPostRepository)
        val slotUseCases = PostingSlotUseCases(postingSlotRepository)

        val api = CalendarApi(eventUseCases, rescheduleUseCase, queueUseCases, slotUseCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8090/api/workspaces/${workspaceId}/queues"))
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
            java.net.InetSocketAddress("localhost", 8090), 0
        ).apply {
            createContext("/", handler)
            executor = null
        }
    }
}
