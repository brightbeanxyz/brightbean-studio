package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Queue
import java.util.UUID

interface QueueRepository {
    fun findById(id: UUID): Queue?
    fun findByWorkspaceId(workspaceId: UUID): List<Queue>
    fun save(queue: Queue): Queue
    fun update(queue: Queue): Queue
    fun delete(id: UUID)
}
