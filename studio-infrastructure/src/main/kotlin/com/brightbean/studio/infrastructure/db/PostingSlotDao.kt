package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.LocalTime
import java.util.UUID

@RegisterKotlinMapper(PostingSlotDto::class)
interface PostingSlotDao {
    @SqlQuery("SELECT * FROM calendar_posting_slot WHERE id = :id")
    fun findById(id: UUID): PostingSlotDto?

    @SqlQuery("SELECT * FROM calendar_posting_slot WHERE social_account_id = :socialAccountId ORDER BY day_of_week, time")
    fun findBySocialAccountId(socialAccountId: UUID): List<PostingSlotDto>

    @SqlQuery("SELECT * FROM calendar_posting_slot WHERE social_account_id = :socialAccountId AND is_active = TRUE ORDER BY day_of_week, time")
    fun findActiveBySocialAccountId(socialAccountId: UUID): List<PostingSlotDto>

    @SqlUpdate("""
        INSERT INTO calendar_posting_slot (id, social_account_id, day_of_week, time, is_active, created_at, updated_at)
        VALUES (:dto.id, :dto.socialAccountId, :dto.dayOfWeek, :dto.time, :dto.isActive, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: PostingSlotDto)

    @SqlUpdate("""
        UPDATE calendar_posting_slot SET
            day_of_week = :dto.dayOfWeek,
            time = :dto.time,
            is_active = :dto.isActive,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PostingSlotDto)

    @SqlUpdate("DELETE FROM calendar_posting_slot WHERE id = :id")
    fun delete(id: UUID)
}

data class PostingSlotDto(
    val id: UUID,
    val socialAccountId: UUID,
    val dayOfWeek: Int,
    val time: LocalTime,
    val isActive: Boolean,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
