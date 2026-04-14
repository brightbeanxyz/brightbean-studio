package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.InboxItem
import java.util.UUID

interface InboxRepository {
    fun findById(id: UUID): InboxItem?
    fun findByWorkspaceId(workspaceId: UUID): List<InboxItem>
    fun findBySocialAccountId(socialAccountId: UUID): List<InboxItem>
    fun save(inboxItem: InboxItem): InboxItem
    fun update(inboxItem: InboxItem): InboxItem
    fun delete(id: UUID)
}