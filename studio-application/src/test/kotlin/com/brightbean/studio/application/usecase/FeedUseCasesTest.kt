package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Feed
import com.brightbean.studio.domain.repository.FeedRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.util.UUID

class FeedUseCasesTest {

    private lateinit var repository: FeedInMemoryRepository
    private lateinit var useCases: FeedUseCases

    @BeforeEach
    fun setUp() {
        repository = FeedInMemoryRepository()
        useCases = FeedUseCases(repository)
    }

    @Test
    fun `add feed`() {
        val workspaceId = UUID.randomUUID()
        val feed = useCases.add(workspaceId, "Tech Blog", "https://example.com/rss", "https://example.com", null)

        assertEquals("Tech Blog", feed.name)
        assertEquals("https://example.com/rss", feed.url)
        assertEquals("https://example.com", feed.websiteUrl)
        assertEquals(workspaceId, feed.workspaceId)
    }

    @Test
    fun `delete feed`() {
        val workspaceId = UUID.randomUUID()
        val feed = useCases.add(workspaceId, "Blog", "https://example.com/rss", "https://example.com", null)

        useCases.delete(feed.id)

        assertTrue(useCases.list(workspaceId).isEmpty())
    }
}

class FeedInMemoryRepository : FeedRepository {
    private val items = mutableMapOf<UUID, Feed>()

    override fun findById(id: UUID): Feed? = items[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Feed> =
        items.values.filter { it.workspaceId == workspaceId }
    override fun save(feed: Feed): Feed { items[feed.id] = feed; return feed }
    override fun delete(id: UUID) { items.remove(id) }
}
