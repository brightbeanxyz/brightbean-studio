package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PublishingQueue
import java.util.UUID

interface PublishingQueueRepository {
    fun findById(id: UUID): PublishingQueue?
    fun findByPostId(postId: UUID): List<PublishingQueue>
    fun findByWorkspaceId(workspaceId: UUID): List<PublishingQueue>
    fun findPending(): List<PublishingQueue>
    fun save(queue: PublishingQueue): PublishingQueue
    fun update(queue: PublishingQueue): PublishingQueue
    fun delete(id: UUID)
}
