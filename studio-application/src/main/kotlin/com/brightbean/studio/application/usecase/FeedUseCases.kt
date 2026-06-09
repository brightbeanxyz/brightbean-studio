package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Feed
import com.brightbean.studio.domain.repository.FeedRepository
import java.time.Instant
import java.util.UUID

class FeedUseCases(private val repository: FeedRepository) {

    fun list(workspaceId: UUID): List<Feed> =
        repository.findByWorkspaceId(workspaceId)

    fun add(workspaceId: UUID, name: String, url: String, websiteUrl: String, addedBy: UUID?): Feed {
        val feed = Feed(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = name,
            url = url,
            websiteUrl = websiteUrl,
            addedBy = addedBy,
            createdAt = Instant.now(),
        )
        return repository.save(feed)
    }

    fun delete(id: UUID) {
        repository.delete(id)
    }
}
