package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.util.UUID

class CalendarEntryTest {

    @Test
    fun `time slots with same time and RESERVED status should be overlapping`() {
        val accountId1 = UUID.randomUUID()
        val accountId2 = UUID.randomUUID()
        
        val timeSlots = listOf(
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = listOf(accountId1),
                status = SlotStatus.RESERVED
            ),
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = listOf(accountId2),
                status = SlotStatus.RESERVED
            )
        )
        
        val calendarEntry = CalendarEntry(
            id = UUID.randomUUID(),
            workspaceId = UUID.randomUUID(),
            postId = UUID.randomUUID(),
            date = LocalDate.now(),
            timeSlots = timeSlots,
            createdAt = Instant.now()
        )
        
        assertTrue(hasOverlappingTimeSlots(calendarEntry))
    }

    @Test
    fun `time slots with different times should not be overlapping`() {
        val accountId = UUID.randomUUID()
        
        val timeSlots = listOf(
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = listOf(accountId),
                status = SlotStatus.RESERVED
            ),
            TimeSlot(
                time = LocalTime.of(11, 0),
                socialAccountIds = listOf(accountId),
                status = SlotStatus.RESERVED
            )
        )
        
        val calendarEntry = CalendarEntry(
            id = UUID.randomUUID(),
            workspaceId = UUID.randomUUID(),
            postId = UUID.randomUUID(),
            date = LocalDate.now(),
            timeSlots = timeSlots,
            createdAt = Instant.now()
        )
        
        assertFalse(hasOverlappingTimeSlots(calendarEntry))
    }

    @Test
    fun `time slots with FREE status should not be considered overlapping`() {
        val timeSlots = listOf(
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = emptyList(),
                status = SlotStatus.FREE
            ),
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = emptyList(),
                status = SlotStatus.FREE
            )
        )
        
        val calendarEntry = CalendarEntry(
            id = UUID.randomUUID(),
            workspaceId = UUID.randomUUID(),
            postId = UUID.randomUUID(),
            date = LocalDate.now(),
            timeSlots = timeSlots,
            createdAt = Instant.now()
        )
        
        assertFalse(hasOverlappingTimeSlots(calendarEntry))
    }

    @Test
    fun `time slots with PUBLISHED status should not be considered overlapping`() {
        val timeSlots = listOf(
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = listOf(UUID.randomUUID()),
                status = SlotStatus.PUBLISHED
            ),
            TimeSlot(
                time = LocalTime.of(10, 0),
                socialAccountIds = listOf(UUID.randomUUID()),
                status = SlotStatus.PUBLISHED
            )
        )
        
        val calendarEntry = CalendarEntry(
            id = UUID.randomUUID(),
            workspaceId = UUID.randomUUID(),
            postId = UUID.randomUUID(),
            date = LocalDate.now(),
            timeSlots = timeSlots,
            createdAt = Instant.now()
        )
        
        assertFalse(hasOverlappingTimeSlots(calendarEntry))
    }

    private fun hasOverlappingTimeSlots(entry: CalendarEntry): Boolean {
        val reservedSlots = entry.timeSlots.filter { it.status == SlotStatus.RESERVED }
        val timeToSlots = reservedSlots.groupBy { it.time }
        return timeToSlots.any { (_, slots) -> slots.size > 1 }
    }
}
