package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Queue
import com.brightbean.studio.domain.repository.QueueRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIQueueRepository(jdbi: Jdbi) : QueueRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: QueueDao by lazy { jdbi.onDemand(QueueDao::class.java) }

    override fun findById(id: UUID): Queue? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Queue> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(queue: Queue): Queue {
        dao.insert(queue.toDto())
        return queue
    }

    override fun update(queue: Queue): Queue {
        dao.update(queue.toDto())
        return queue
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun Queue.toDto() = QueueDto(
        id = id, workspaceId = workspaceId, name = name, categoryId = categoryId,
        socialAccountId = socialAccountId, isActive = isActive,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun QueueDto.toDomain() = Queue(
        id = id, workspaceId = workspaceId, name = name, categoryId = categoryId,
        socialAccountId = socialAccountId, isActive = isActive,
        createdAt = createdAt, updatedAt = updatedAt,
    )
}
