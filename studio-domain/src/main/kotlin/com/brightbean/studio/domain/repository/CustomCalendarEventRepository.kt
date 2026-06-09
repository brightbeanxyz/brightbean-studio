package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.CustomCalendarEvent
import java.time.LocalDate
import java.util.UUID

interface CustomCalendarEventRepository {
    fun findById(id: UUID): CustomCalendarEvent?
    fun findByWorkspaceId(workspaceId: UUID): List<CustomCalendarEvent>
    fun findByDateRange(workspaceId: UUID, startDate: LocalDate, endDate: LocalDate): List<CustomCalendarEvent>
    fun save(event: CustomCalendarEvent): CustomCalendarEvent
    fun update(event: CustomCalendarEvent): CustomCalendarEvent
    fun delete(id: UUID)
}
