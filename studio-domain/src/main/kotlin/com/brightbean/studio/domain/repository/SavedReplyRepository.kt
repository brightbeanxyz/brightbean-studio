package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.SavedReply
import java.util.UUID

interface SavedReplyRepository {
    fun findByWorkspaceId(workspaceId: UUID): List<SavedReply>
    fun save(reply: SavedReply): SavedReply
    fun update(reply: SavedReply): SavedReply
    fun delete(id: UUID)
}
