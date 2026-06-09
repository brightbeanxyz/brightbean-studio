package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.CustomCalendarEvent
import com.brightbean.studio.domain.repository.CustomCalendarEventRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.time.LocalDate
import java.util.UUID

class JDBICustomCalendarEventRepository(jdbi: Jdbi) : CustomCalendarEventRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: CustomCalendarEventDao by lazy { jdbi.onDemand(CustomCalendarEventDao::class.java) }

    override fun findById(id: UUID): CustomCalendarEvent? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<CustomCalendarEvent> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByDateRange(workspaceId: UUID, startDate: LocalDate, endDate: LocalDate): List<CustomCalendarEvent> =
        dao.findByDateRange(workspaceId, startDate, endDate).map { it.toDomain() }

    override fun save(event: CustomCalendarEvent): CustomCalendarEvent {
        dao.insert(event.toDto())
        return event
    }

    override fun update(event: CustomCalendarEvent): CustomCalendarEvent {
        dao.update(event.toDto())
        return event
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun CustomCalendarEvent.toDto() = CustomCalendarEventDto(
        id = id, workspaceId = workspaceId, title = title, description = description,
        startDate = startDate, endDate = endDate, color = color, createdBy = createdBy,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun CustomCalendarEventDto.toDomain() = CustomCalendarEvent(
        id = id, workspaceId = workspaceId, title = title, description = description,
        startDate = startDate, endDate = endDate, color = color, createdBy = createdBy,
        createdAt = createdAt, updatedAt = updatedAt,
    )
}
