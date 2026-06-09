package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Feed
import java.util.UUID

interface FeedRepository {
    fun findById(id: UUID): Feed?
    fun findByWorkspaceId(workspaceId: UUID): List<Feed>
    fun save(feed: Feed): Feed
    fun delete(id: UUID)
}
