package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Feed
import com.brightbean.studio.domain.repository.FeedRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIFeedRepository(jdbi: Jdbi) : FeedRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: FeedDao by lazy { jdbi.onDemand(FeedDao::class.java) }

    override fun findById(id: UUID): Feed? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Feed> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(feed: Feed): Feed {
        dao.insert(feed.toDto())
        return feed
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun Feed.toDto() = FeedDto(
        id = id, workspaceId = workspaceId, name = name, url = url,
        websiteUrl = websiteUrl, addedBy = addedBy, createdAt = createdAt,
    )

    private fun FeedDto.toDomain() = Feed(
        id = id, workspaceId = workspaceId, name = name, url = url,
        websiteUrl = websiteUrl, addedBy = addedBy, createdAt = createdAt,
    )
}
