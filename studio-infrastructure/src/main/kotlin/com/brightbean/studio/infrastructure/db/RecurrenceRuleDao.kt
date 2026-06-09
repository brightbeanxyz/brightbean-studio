package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.LocalDate
import java.util.UUID

@RegisterKotlinMapper(RecurrenceRuleDto::class)
interface RecurrenceRuleDao {
    @SqlQuery("SELECT * FROM calendar_recurrence_rule WHERE post_id = :postId")
    fun findByPostId(postId: UUID): RecurrenceRuleDto?

    @SqlQuery("SELECT * FROM calendar_recurrence_rule WHERE is_active = TRUE")
    fun findActive(): List<RecurrenceRuleDto>

    @SqlUpdate("""
        INSERT INTO calendar_recurrence_rule (id, post_id, frequency, interval_days, end_date, last_generated_at, is_active, created_at)
        VALUES (:dto.id, :dto.postId, :dto.frequency, :dto.intervalDays, :dto.endDate, :dto.lastGeneratedAt, :dto.isActive, :dto.createdAt)
    """)
    fun insert(dto: RecurrenceRuleDto)

    @SqlUpdate("""
        UPDATE calendar_recurrence_rule SET
            frequency = :dto.frequency,
            interval_days = :dto.intervalDays,
            end_date = :dto.endDate,
            last_generated_at = :dto.lastGeneratedAt,
            is_active = :dto.isActive
        WHERE id = :dto.id
    """)
    fun update(dto: RecurrenceRuleDto)

    @SqlUpdate("DELETE FROM calendar_recurrence_rule WHERE id = :id")
    fun delete(id: UUID)
}

data class RecurrenceRuleDto(
    val id: UUID,
    val postId: UUID,
    val frequency: String,
    val intervalDays: Int,
    val endDate: LocalDate?,
    val lastGeneratedAt: java.time.Instant?,
    val isActive: Boolean,
    val createdAt: java.time.Instant,
)
