package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.CustomCalendarEvent
import com.brightbean.studio.domain.repository.CustomCalendarEventRepository
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

class CustomCalendarEventUseCases(private val repository: CustomCalendarEventRepository) {

    fun list(workspaceId: UUID): List<CustomCalendarEvent> =
        repository.findByWorkspaceId(workspaceId)

    fun findByDateRange(workspaceId: UUID, startDate: LocalDate, endDate: LocalDate): List<CustomCalendarEvent> =
        repository.findByDateRange(workspaceId, startDate, endDate)

    fun create(
        workspaceId: UUID,
        title: String,
        description: String,
        startDate: LocalDate,
        endDate: LocalDate,
        color: String,
        createdBy: UUID?,
    ): CustomCalendarEvent {
        val event = CustomCalendarEvent(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            title = title,
            description = description,
            startDate = startDate,
            endDate = endDate,
            color = color,
            createdBy = createdBy,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return repository.save(event)
    }

    fun update(
        id: UUID,
        title: String?,
        description: String?,
        startDate: LocalDate?,
        endDate: LocalDate?,
        color: String?,
    ): CustomCalendarEvent {
        val event = repository.findById(id)
            ?: throw IllegalArgumentException("Event not found: $id")
        val updated = event.copy(
            title = title ?: event.title,
            description = description ?: event.description,
            startDate = startDate ?: event.startDate,
            endDate = endDate ?: event.endDate,
            color = color ?: event.color,
            updatedAt = Instant.now(),
        )
        return repository.update(updated)
    }

    fun delete(id: UUID) {
        repository.delete(id)
    }
}
