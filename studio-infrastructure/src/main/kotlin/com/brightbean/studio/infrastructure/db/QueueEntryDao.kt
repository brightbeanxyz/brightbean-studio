package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(QueueEntryDto::class)
interface QueueEntryDao {
    @SqlQuery("SELECT * FROM calendar_queue_entry WHERE queue_id = :queueId ORDER BY position")
    fun findByQueueId(queueId: UUID): List<QueueEntryDto>

    @SqlUpdate("""
        INSERT INTO calendar_queue_entry (id, queue_id, post_id, position, assigned_slot_datetime, created_at)
        VALUES (:dto.id, :dto.queueId, :dto.postId, :dto.position, :dto.assignedSlotDatetime, :dto.createdAt)
    """)
    fun insert(dto: QueueEntryDto)

    @SqlUpdate("""
        UPDATE calendar_queue_entry SET
            position = :dto.position,
            assigned_slot_datetime = :dto.assignedSlotDatetime
        WHERE id = :dto.id
    """)
    fun update(dto: QueueEntryDto)

    @SqlUpdate("DELETE FROM calendar_queue_entry WHERE id = :id")
    fun delete(id: UUID)

    @SqlUpdate("DELETE FROM calendar_queue_entry WHERE queue_id = :queueId")
    fun deleteByQueueId(queueId: UUID)
}

data class QueueEntryDto(
    val id: UUID,
    val queueId: UUID,
    val postId: UUID,
    val position: Int,
    val assignedSlotDatetime: java.time.Instant?,
    val createdAt: java.time.Instant,
)
