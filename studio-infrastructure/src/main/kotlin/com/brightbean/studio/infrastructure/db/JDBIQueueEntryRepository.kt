package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.QueueEntry
import com.brightbean.studio.domain.repository.QueueEntryRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIQueueEntryRepository(jdbi: Jdbi) : QueueEntryRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: QueueEntryDao by lazy { jdbi.onDemand(QueueEntryDao::class.java) }

    override fun findByQueueId(queueId: UUID): List<QueueEntry> =
        dao.findByQueueId(queueId).map { it.toDomain() }

    override fun save(entry: QueueEntry): QueueEntry {
        dao.insert(entry.toDto())
        return entry
    }

    override fun update(entry: QueueEntry): QueueEntry {
        dao.update(entry.toDto())
        return entry
    }

    override fun delete(id: UUID) = dao.delete(id)

    override fun deleteByQueueId(queueId: UUID) = dao.deleteByQueueId(queueId)

    private fun QueueEntry.toDto() = QueueEntryDto(
        id = id, queueId = queueId, postId = postId, position = position,
        assignedSlotDatetime = assignedSlotDatetime, createdAt = createdAt,
    )

    private fun QueueEntryDto.toDomain() = QueueEntry(
        id = id, queueId = queueId, postId = postId, position = position,
        assignedSlotDatetime = assignedSlotDatetime, createdAt = createdAt,
    )
}
