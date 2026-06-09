package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.CustomCalendarEventUseCases
import com.brightbean.studio.application.usecase.PostingSlotUseCases
import com.brightbean.studio.application.usecase.QueueUseCases
import com.brightbean.studio.application.usecase.ReschedulePostUseCase
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.InputStreamReader
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.util.UUID

class CalendarApi(
    private val calendarEventUseCases: CustomCalendarEventUseCases,
    private val reschedulePostUseCase: ReschedulePostUseCase,
    private val queueUseCases: QueueUseCases,
    private val postingSlotUseCases: PostingSlotUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .registerTypeAdapter(LocalDate::class.java, LocalDateAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/calendar/events/[^/]+$")) && method == "PUT" -> updateEvent(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/calendar/events/[^/]+$")) && method == "DELETE" -> deleteEvent(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/calendar/events$")) && method == "GET" -> listEvents(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/calendar/events$")) && method == "POST" -> createEvent(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/calendar/reschedule$")) && method == "POST" -> reschedulePost(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/queues/[^/]+/entries$")) && method == "GET" -> listQueueEntries(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/queues/[^/]+/entries$")) && method == "POST" -> addToQueue(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/queues/[^/]+/reorder$")) && method == "POST" -> reorderQueue(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/queues/[^/]+$")) && method == "DELETE" -> deleteQueue(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/queues$")) && method == "GET" -> listQueues(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/queues$")) && method == "POST" -> createQueue(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/posting-slots/[^/]+$")) && method == "PUT" -> updateSlot(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/posting-slots/[^/]+$")) && method == "DELETE" -> deleteSlot(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/posting-slots$")) && method == "GET" -> listSlots(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/posting-slots$")) && method == "POST" -> createSlot(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listEvents(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val queryParams = parseQueryParams(exchange.requestURI.query ?: "")
            val start = queryParams["start"]
            val end = queryParams["end"]

            val events = if (start != null && end != null) {
                calendarEventUseCases.findByDateRange(workspaceId, LocalDate.parse(start), LocalDate.parse(end))
            } else {
                calendarEventUseCases.list(workspaceId)
            }
            sendJson(exchange, 200, events)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createEvent(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateEventRequest::class.java)

            val event = calendarEventUseCases.create(
                workspaceId = workspaceId,
                title = request.title,
                description = request.description ?: "",
                startDate = LocalDate.parse(request.startDate),
                endDate = LocalDate.parse(request.endDate),
                color = request.color ?: "#4285F4",
                createdBy = null,
            )
            sendJson(exchange, 201, event)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create event")
        }
    }

    private fun updateEvent(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val eventId = UUID.fromString(pathParts[6])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateEventRequest::class.java)

            val event = calendarEventUseCases.update(
                id = eventId,
                title = request.title,
                description = request.description,
                startDate = request.startDate?.let { LocalDate.parse(it) },
                endDate = request.endDate?.let { LocalDate.parse(it) },
                color = request.color,
            )
            sendJson(exchange, 200, event)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update event")
        }
    }

    private fun deleteEvent(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val eventId = UUID.fromString(pathParts[6])

            calendarEventUseCases.delete(eventId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete event")
        }
    }

    private fun reschedulePost(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, RescheduleRequest::class.java)

            if (request.platformPostId != null) {
                reschedulePostUseCase.execute(request.platformPostId, request.newDatetime)
            } else if (request.postId != null) {
                reschedulePostUseCase.executeByPost(request.postId, request.newDatetime)
            } else {
                sendError(exchange, 400, "platformPostId or postId required"); return
            }

            sendJson(exchange, 200, mapOf("rescheduled" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to reschedule")
        }
    }

    private fun listQueues(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val queues = queueUseCases.list(workspaceId)
            sendJson(exchange, 200, queues)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createQueue(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateQueueRequest::class.java)

            val queue = queueUseCases.create(workspaceId, request.name, request.socialAccountId, request.categoryId)
            sendJson(exchange, 201, queue)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create queue")
        }
    }

    private fun deleteQueue(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val queueId = UUID.fromString(pathParts[5])

            queueUseCases.delete(queueId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete queue")
        }
    }

    private fun listQueueEntries(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val queueId = UUID.fromString(pathParts[5])
            val entries = queueUseCases.getEntries(queueId)
            sendJson(exchange, 200, entries)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun addToQueue(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val queueId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, AddToQueueRequest::class.java)

            val entry = queueUseCases.addToQueue(queueId, request.postId, request.priority ?: false)
            sendJson(exchange, 201, entry)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to add to queue")
        }
    }

    private fun reorderQueue(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val queueId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, ReorderQueueRequest::class.java)

            queueUseCases.reorder(queueId, request.orderedEntryIds)
            sendJson(exchange, 200, mapOf("reordered" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to reorder queue")
        }
    }

    private fun listSlots(exchange: HttpExchange) {
        try {
            val queryParams = parseQueryParams(exchange.requestURI.query ?: "")
            val accountId = queryParams["account"]?.let { UUID.fromString(it) }

            if (accountId == null) {
                sendError(exchange, 400, "account query parameter required"); return
            }

            val slots = postingSlotUseCases.findByAccount(accountId)
            sendJson(exchange, 200, slots)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createSlot(exchange: HttpExchange) {
        try {
            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateSlotRequest::class.java)

            val slot = postingSlotUseCases.create(
                socialAccountId = request.socialAccountId,
                dayOfWeek = request.dayOfWeek,
                time = LocalTime.parse(request.time),
            )
            sendJson(exchange, 201, slot)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create slot")
        }
    }

    private fun updateSlot(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val slotId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateSlotRequest::class.java)

            val slot = postingSlotUseCases.update(slotId, LocalTime.parse(request.time))
            sendJson(exchange, 200, slot)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update slot")
        }
    }

    private fun deleteSlot(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val slotId = UUID.fromString(pathParts[5])

            postingSlotUseCases.delete(slotId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete slot")
        }
    }

    private fun parseQueryParams(query: String): Map<String, String> {
        if (query.isBlank()) return emptyMap()
        return query.split("&")
            .mapNotNull { param ->
                val parts = param.split("=")
                if (parts.size == 2) parts[0] to parts[1] else null
            }
            .toMap()
    }

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(
            error = when (statusCode) {
                400 -> "Bad Request"
                403 -> "Forbidden"
                404 -> "Not Found"
                500 -> "Internal Server Error"
                else -> "Error"
            },
            message = message,
            statusCode = statusCode,
        )
        sendJson(exchange, statusCode, error)
    }

    private data class CreateEventRequest(
        val title: String,
        val description: String? = null,
        val startDate: String,
        val endDate: String,
        val color: String? = null,
    )

    private data class UpdateEventRequest(
        val title: String? = null,
        val description: String? = null,
        val startDate: String? = null,
        val endDate: String? = null,
        val color: String? = null,
    )

    private data class RescheduleRequest(
        val platformPostId: UUID? = null,
        val postId: UUID? = null,
        val newDatetime: Instant,
    )

    private data class CreateQueueRequest(
        val name: String,
        val socialAccountId: UUID,
        val categoryId: UUID? = null,
    )

    private data class AddToQueueRequest(
        val postId: UUID,
        val priority: Boolean? = null,
    )

    private data class ReorderQueueRequest(
        val orderedEntryIds: List<UUID>,
    )

    private data class CreateSlotRequest(
        val socialAccountId: UUID,
        val dayOfWeek: Int,
        val time: String,
    )

    private data class UpdateSlotRequest(
        val time: String,
    )
}

class LocalDateAdapter : com.google.gson.TypeAdapter<LocalDate>() {
    override fun write(out: com.google.gson.stream.JsonWriter, value: LocalDate?) {
        if (value == null) {
            out.nullValue()
        } else {
            out.value(value.toString())
        }
    }

    override fun read(input: com.google.gson.stream.JsonReader): LocalDate? {
        return if (input.peek() == com.google.gson.stream.JsonToken.NULL) {
            input.nextNull()
            null
        } else {
            LocalDate.parse(input.nextString())
        }
    }
}
