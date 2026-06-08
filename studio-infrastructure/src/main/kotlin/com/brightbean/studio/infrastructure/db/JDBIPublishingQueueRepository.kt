package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PublishingQueue
import com.brightbean.studio.domain.model.QueueStatus
import com.brightbean.studio.domain.repository.PublishingQueueRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPublishingQueueRepository(jdbi: Jdbi) : PublishingQueueRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PublishingQueueDao by lazy { jdbi.onDemand(PublishingQueueDao::class.java) }

    override fun findById(id: UUID): PublishingQueue? =
        dao.findById(id)?.toDomain()

    override fun findByPostId(postId: UUID): List<PublishingQueue> =
        dao.findByPostId(postId).map { it.toDomain() }

    override fun findByWorkspaceId(workspaceId: UUID): List<PublishingQueue> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findPending(): List<PublishingQueue> =
        dao.findPending().map { it.toDomain() }

    override fun save(queue: PublishingQueue): PublishingQueue {
        dao.insert(queue.toDto())
        return queue
    }

    override fun update(queue: PublishingQueue): PublishingQueue {
        dao.update(queue.toDto())
        return queue
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun PublishingQueue.toDto() = PublishingQueueDto(
        id = id,
        workspaceId = workspaceId,
        postId = postId,
        scheduledFor = scheduledFor,
        attempts = attempts,
        lastAttemptAt = lastAttemptAt,
        status = status.name,
        errorMessage = errorMessage,
    )

    private fun PublishingQueueDto.toDomain() = PublishingQueue(
        id = id,
        workspaceId = workspaceId,
        postId = postId,
        scheduledFor = scheduledFor,
        attempts = attempts,
        lastAttemptAt = lastAttemptAt,
        status = QueueStatus.valueOf(status),
        errorMessage = errorMessage,
    )
}
