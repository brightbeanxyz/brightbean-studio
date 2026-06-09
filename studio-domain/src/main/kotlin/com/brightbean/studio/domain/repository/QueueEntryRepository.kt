package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.QueueEntry
import java.util.UUID

interface QueueEntryRepository {
    fun findByQueueId(queueId: UUID): List<QueueEntry>
    fun save(entry: QueueEntry): QueueEntry
    fun update(entry: QueueEntry): QueueEntry
    fun delete(id: UUID)
    fun deleteByQueueId(queueId: UUID)
}
