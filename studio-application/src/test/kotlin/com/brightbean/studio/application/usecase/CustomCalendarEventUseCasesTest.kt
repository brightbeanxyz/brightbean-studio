package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.CustomCalendarEvent
import com.brightbean.studio.domain.repository.CustomCalendarEventRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.LocalDate
import java.util.UUID

class CustomCalendarEventUseCasesTest {

    private lateinit var repository: CalendarEventInMemoryRepository
    private lateinit var useCases: CustomCalendarEventUseCases

    @BeforeEach
    fun setUp() {
        repository = CalendarEventInMemoryRepository()
        useCases = CustomCalendarEventUseCases(repository)
    }

    @Test
    fun `create event`() {
        val workspaceId = UUID.randomUUID()
        val event = useCases.create(
            workspaceId,
            "Team Meeting",
            "Weekly sync",
            LocalDate.of(2026, 1, 1),
            LocalDate.of(2026, 1, 2),
            "#FF0000",
            null,
        )

        assertEquals("Team Meeting", event.title)
        assertEquals("Weekly sync", event.description)
        assertEquals(workspaceId, event.workspaceId)
        assertEquals("#FF0000", event.color)
    }

    @Test
    fun `update event`() {
        val workspaceId = UUID.randomUUID()
        val created = useCases.create(workspaceId, "Old", "Desc", LocalDate.of(2026, 1, 1), LocalDate.of(2026, 1, 2), "#000000", null)

        val updated = useCases.update(created.id, "New", null, null, null, "#FFFFFF")

        assertEquals("New", updated.title)
        assertEquals("Desc", updated.description)
        assertEquals("#FFFFFF", updated.color)
    }

    @Test
    fun `delete event`() {
        val workspaceId = UUID.randomUUID()
        val created = useCases.create(workspaceId, "Delete Me", "", LocalDate.of(2026, 1, 1), LocalDate.of(2026, 1, 2), "#000000", null)

        useCases.delete(created.id)

        assertTrue(useCases.list(workspaceId).isEmpty())
    }
}

class CalendarEventInMemoryRepository : CustomCalendarEventRepository {
    private val items = mutableMapOf<UUID, CustomCalendarEvent>()

    override fun findById(id: UUID): CustomCalendarEvent? = items[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<CustomCalendarEvent> =
        items.values.filter { it.workspaceId == workspaceId }
    override fun findByDateRange(workspaceId: UUID, startDate: LocalDate, endDate: LocalDate): List<CustomCalendarEvent> =
        items.values.filter { it.workspaceId == workspaceId && it.startDate <= endDate && it.endDate >= startDate }
    override fun save(event: CustomCalendarEvent): CustomCalendarEvent { items[event.id] = event; return event }
    override fun update(event: CustomCalendarEvent): CustomCalendarEvent { items[event.id] = event; return event }
    override fun delete(id: UUID) { items.remove(id) }
}
