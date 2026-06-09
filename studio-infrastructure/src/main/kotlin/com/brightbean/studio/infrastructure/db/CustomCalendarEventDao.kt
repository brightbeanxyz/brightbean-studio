package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.LocalDate
import java.util.UUID

@RegisterKotlinMapper(CustomCalendarEventDto::class)
interface CustomCalendarEventDao {
    @SqlQuery("SELECT * FROM calendar_custom_event WHERE id = :id")
    fun findById(id: UUID): CustomCalendarEventDto?

    @SqlQuery("SELECT * FROM calendar_custom_event WHERE workspace_id = :workspaceId ORDER BY start_date")
    fun findByWorkspaceId(workspaceId: UUID): List<CustomCalendarEventDto>

    @SqlQuery("SELECT * FROM calendar_custom_event WHERE workspace_id = :workspaceId AND start_date <= :endDate AND end_date >= :startDate ORDER BY start_date")
    fun findByDateRange(workspaceId: UUID, startDate: LocalDate, endDate: LocalDate): List<CustomCalendarEventDto>

    @SqlUpdate("""
        INSERT INTO calendar_custom_event (id, workspace_id, title, description, start_date, end_date, color, created_by, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.title, :dto.description, :dto.startDate, :dto.endDate, :dto.color, :dto.createdBy, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: CustomCalendarEventDto)

    @SqlUpdate("""
        UPDATE calendar_custom_event SET
            title = :dto.title,
            description = :dto.description,
            start_date = :dto.startDate,
            end_date = :dto.endDate,
            color = :dto.color,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: CustomCalendarEventDto)

    @SqlUpdate("DELETE FROM calendar_custom_event WHERE id = :id")
    fun delete(id: UUID)
}

data class CustomCalendarEventDto(
    val id: UUID,
    val workspaceId: UUID,
    val title: String,
    val description: String,
    val startDate: LocalDate,
    val endDate: LocalDate,
    val color: String,
    val createdBy: UUID?,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
