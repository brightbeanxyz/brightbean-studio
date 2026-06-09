package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostingSlot
import com.brightbean.studio.domain.model.Queue
import com.brightbean.studio.domain.model.QueueEntry
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.QueueEntryRepository
import com.brightbean.studio.domain.repository.QueueRepository
import com.brightbean.studio.domain.repository.PostingSlotRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.time.LocalTime
import java.util.UUID

class QueueUseCasesTest {

    private lateinit var queueRepo: QueueInMemoryRepository
    private lateinit var queueEntryRepo: QueueEntryInMemoryRepository
    private lateinit var postingSlotRepo: PostingSlotInMemRepository
    private lateinit var postRepo: PostInMemoryRepository
    private lateinit var platformPostRepo: PlatformPostInMemoryRepository
    private lateinit var useCases: QueueUseCases

    @BeforeEach
    fun setUp() {
        queueRepo = QueueInMemoryRepository()
        queueEntryRepo = QueueEntryInMemoryRepository()
        postingSlotRepo = PostingSlotInMemRepository()
        postRepo = PostInMemoryRepository()
        platformPostRepo = PlatformPostInMemoryRepository()
        useCases = QueueUseCases(queueRepo, queueEntryRepo, postingSlotRepo, postRepo, platformPostRepo)
    }

    @Test
    fun `create queue`() {
        val workspaceId = UUID.randomUUID()
        val accountId = UUID.randomUUID()
        val queue = useCases.create(workspaceId, "Main Queue", accountId, null)

        assertEquals("Main Queue", queue.name)
        assertEquals(workspaceId, queue.workspaceId)
        assertEquals(accountId, queue.socialAccountId)
        assertTrue(queue.isActive)
    }

    @Test
    fun `add to queue appends at end`() {
        val queue = useCases.create(UUID.randomUUID(), "Q", UUID.randomUUID(), null)
        val post1 = saveTestPost()
        val post2 = saveTestPost()

        val entry1 = useCases.addToQueue(queue.id, post1.id)
        val entry2 = useCases.addToQueue(queue.id, post2.id)

        assertEquals(0, entry1.position)
        assertEquals(1, entry2.position)
    }

    @Test
    fun `add to queue with priority inserts at position 0`() {
        val queue = useCases.create(UUID.randomUUID(), "Q", UUID.randomUUID(), null)
        val post1 = saveTestPost()
        val post2 = saveTestPost()

        useCases.addToQueue(queue.id, post1.id)
        val priorityEntry = useCases.addToQueue(queue.id, post2.id, priority = true)

        assertEquals(0, priorityEntry.position)
        val entries = useCases.getEntries(queue.id)
        assertEquals(2, entries.size)
        assertEquals(1, entries.find { it.id != priorityEntry.id }?.position)
    }

    @Test
    fun `delete queue cascades entries`() {
        val queue = useCases.create(UUID.randomUUID(), "Q", UUID.randomUUID(), null)
        val post = saveTestPost()
        useCases.addToQueue(queue.id, post.id)

        useCases.delete(queue.id)

        assertNull(queueRepo.findById(queue.id))
        assertTrue(queueEntryRepo.findByQueueId(queue.id).isEmpty())
    }

    @Test
    fun `reorder entries`() {
        val queue = useCases.create(UUID.randomUUID(), "Q", UUID.randomUUID(), null)
        val post1 = saveTestPost()
        val post2 = saveTestPost()
        val entry1 = useCases.addToQueue(queue.id, post1.id)
        val entry2 = useCases.addToQueue(queue.id, post2.id)

        useCases.reorder(queue.id, listOf(entry2.id, entry1.id))

        val entries = useCases.getEntries(queue.id).sortedBy { it.position }
        assertEquals(entry2.id, entries[0].id)
        assertEquals(entry1.id, entries[1].id)
    }

    private fun saveTestPost(): Post {
        val post = Post(
            id = UUID.randomUUID(),
            workspaceId = UUID.randomUUID(),
            authorId = null,
            title = "",
            caption = "",
            firstComment = "",
            internalNotes = "",
            tags = emptyList(),
            categoryId = null,
            scheduledAt = null,
            publishedAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return postRepo.save(post)
    }
}

class QueueInMemoryRepository : QueueRepository {
    private val items = mutableMapOf<UUID, Queue>()
    override fun findById(id: UUID): Queue? = items[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Queue> = items.values.filter { it.workspaceId == workspaceId }
    override fun save(queue: Queue): Queue { items[queue.id] = queue; return queue }
    override fun update(queue: Queue): Queue { items[queue.id] = queue; return queue }
    override fun delete(id: UUID) { items.remove(id) }
}

class QueueEntryInMemoryRepository : QueueEntryRepository {
    private val items = mutableMapOf<UUID, QueueEntry>()
    override fun findByQueueId(queueId: UUID): List<QueueEntry> = items.values.filter { it.queueId == queueId }
    override fun save(entry: QueueEntry): QueueEntry { items[entry.id] = entry; return entry }
    override fun update(entry: QueueEntry): QueueEntry { items[entry.id] = entry; return entry }
    override fun delete(id: UUID) { items.remove(id) }
    override fun deleteByQueueId(queueId: UUID) { items.entries.removeIf { it.value.queueId == queueId } }
}

class PostingSlotInMemRepository : PostingSlotRepository {
    private val items = mutableMapOf<UUID, PostingSlot>()
    override fun findById(id: UUID): PostingSlot? = items[id]
    override fun findBySocialAccountId(socialAccountId: UUID): List<PostingSlot> = items.values.filter { it.socialAccountId == socialAccountId }
    override fun findActiveBySocialAccountId(socialAccountId: UUID): List<PostingSlot> = items.values.filter { it.socialAccountId == socialAccountId && it.isActive }
    override fun save(slot: PostingSlot): PostingSlot { items[slot.id] = slot; return slot }
    override fun update(slot: PostingSlot): PostingSlot { items[slot.id] = slot; return slot }
    override fun delete(id: UUID) { items.remove(id) }
}

class PostInMemoryRepository : PostRepository {
    private val items = mutableMapOf<UUID, Post>()
    override fun findById(id: UUID): Post? = items[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Post> = items.values.filter { it.workspaceId == workspaceId }
    override fun findByAuthorId(authorId: UUID): List<Post> = items.values.filter { it.authorId == authorId }
    override fun save(post: Post): Post { items[post.id] = post; return post }
    override fun update(post: Post): Post { items[post.id] = post; return post }
    override fun delete(id: UUID) { items.remove(id) }
}

class PlatformPostInMemoryRepository : PlatformPostRepository {
    private val items = mutableMapOf<UUID, PlatformPost>()
    override fun findById(id: UUID): PlatformPost? = items[id]
    override fun findByPostId(postId: UUID): List<PlatformPost> = items.values.filter { it.postId == postId }
    override fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost> = items.values.filter { it.socialAccountId == socialAccountId }
    override fun findByStatus(status: PlatformPostStatus): List<PlatformPost> = items.values.filter { it.status == status }
    override fun findScheduledBefore(time: Instant): List<PlatformPost> = items.values.filter { it.scheduledAt != null && it.scheduledAt!! < time }
    override fun save(platformPost: PlatformPost): PlatformPost { items[platformPost.id] = platformPost; return platformPost }
    override fun update(platformPost: PlatformPost): PlatformPost { items[platformPost.id] = platformPost; return platformPost }
    override fun delete(id: UUID) { items.remove(id) }
}
