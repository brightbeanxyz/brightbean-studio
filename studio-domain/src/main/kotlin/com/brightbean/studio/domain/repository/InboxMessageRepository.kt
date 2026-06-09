package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.InboxMessage
import com.brightbean.studio.domain.model.InboxMessageStatus
import java.util.UUID

interface InboxMessageRepository {
    fun findById(id: UUID): InboxMessage?
    fun findByWorkspaceId(workspaceId: UUID): List<InboxMessage>
    fun findByStatus(workspaceId: UUID, status: InboxMessageStatus): List<InboxMessage>
    fun findByAssignedTo(workspaceId: UUID, userId: UUID): List<InboxMessage>
    fun findByPlatformMessageId(socialAccountId: UUID, platformMessageId: String): InboxMessage?
    fun save(message: InboxMessage): InboxMessage
    fun update(message: InboxMessage): InboxMessage
    fun delete(id: UUID)
}
