package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.InboxMessage
import com.brightbean.studio.domain.model.InboxMessageStatus
import com.brightbean.studio.domain.model.InboxMessageType
import com.brightbean.studio.domain.model.InboxReply
import com.brightbean.studio.domain.model.InternalNote
import com.brightbean.studio.domain.model.InboxSLAConfig
import com.brightbean.studio.domain.model.SavedReply
import com.brightbean.studio.domain.repository.InboxMessageRepository
import com.brightbean.studio.domain.repository.InboxReplyRepository
import com.brightbean.studio.domain.repository.InboxSLAConfigRepository
import com.brightbean.studio.domain.repository.InternalNoteRepository
import com.brightbean.studio.domain.repository.SavedReplyRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class InboxUseCasesTest {

    private lateinit var inboxMessageRepo: InMemInboxMessageRepo
    private lateinit var inboxReplyRepo: InMemInboxReplyRepo
    private lateinit var internalNoteRepo: InMemInternalNoteRepo
    private lateinit var savedReplyRepo: InMemSavedReplyRepo
    private lateinit var inboxSLAConfigRepo: InMemInboxSLAConfigRepo
    private lateinit var useCases: InboxUseCases

    private val workspaceId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        inboxMessageRepo = InMemInboxMessageRepo()
        inboxReplyRepo = InMemInboxReplyRepo()
        internalNoteRepo = InMemInternalNoteRepo()
        savedReplyRepo = InMemSavedReplyRepo()
        inboxSLAConfigRepo = InMemInboxSLAConfigRepo()
        useCases = InboxUseCases(inboxMessageRepo, inboxReplyRepo, internalNoteRepo, savedReplyRepo, inboxSLAConfigRepo)
    }

    @Test
    fun `listMessages returns all messages for workspace`() {
        inboxMessageRepo.save(createMessage(workspaceId = workspaceId))
        inboxMessageRepo.save(createMessage(workspaceId = workspaceId))
        inboxMessageRepo.save(createMessage(workspaceId = UUID.randomUUID()))

        assertEquals(2, useCases.listMessages(workspaceId).size)
    }

    @Test
    fun `listMessages filters by status`() {
        inboxMessageRepo.save(createMessage(workspaceId = workspaceId, status = InboxMessageStatus.UNREAD))
        inboxMessageRepo.save(createMessage(workspaceId = workspaceId, status = InboxMessageStatus.RESOLVED))

        assertEquals(1, useCases.listMessages(workspaceId, InboxMessageStatus.UNREAD).size)
    }

    @Test
    fun `getMessage returns message by id`() {
        val message = createMessage()
        inboxMessageRepo.save(message)

        val found = useCases.getMessage(message.id)
        assertNotNull(found)
        assertEquals(message.id, found!!.id)
    }

    @Test
    fun `sendReply creates reply`() {
        val message = createMessage()
        inboxMessageRepo.save(message)

        val reply = useCases.sendReply(message.id, UUID.randomUUID(), "Thanks!", "reply_123")
        assertEquals("Thanks!", reply.body)
        assertEquals(message.id, reply.inboxMessageId)
    }

    @Test
    fun `addNote creates internal note`() {
        val message = createMessage()
        inboxMessageRepo.save(message)

        val note = useCases.addNote(message.id, UUID.randomUUID(), "Internal note")
        assertEquals("Internal note", note.body)
    }

    @Test
    fun `assignMessage updates assignedTo and status`() {
        val message = createMessage()
        inboxMessageRepo.save(message)
        val userId = UUID.randomUUID()

        val updated = useCases.assignMessage(message.id, userId)
        assertEquals(userId, updated.assignedTo)
        assertEquals(InboxMessageStatus.OPEN, updated.status)
    }

    @Test
    fun `changeStatus updates message status`() {
        val message = createMessage()
        inboxMessageRepo.save(message)

        val updated = useCases.changeStatus(message.id, InboxMessageStatus.RESOLVED)
        assertEquals(InboxMessageStatus.RESOLVED, updated.status)
    }

    @Test
    fun `changeSentiment updates sentiment`() {
        val message = createMessage()
        inboxMessageRepo.save(message)

        val updated = useCases.changeSentiment(message.id, "NEGATIVE", "manual")
        assertEquals("NEGATIVE", updated.sentiment)
        assertEquals("manual", updated.sentimentSource)
    }

    @Test
    fun `bulkAction archives messages`() {
        val m1 = createMessage(); inboxMessageRepo.save(m1)
        val m2 = createMessage(); inboxMessageRepo.save(m2)

        useCases.bulkAction(listOf(m1.id, m2.id), "archive")

        assertEquals(InboxMessageStatus.ARCHIVED, inboxMessageRepo.findById(m1.id)!!.status)
        assertEquals(InboxMessageStatus.ARCHIVED, inboxMessageRepo.findById(m2.id)!!.status)
    }

    @Test
    fun `bulkAction deletes messages`() {
        val m1 = createMessage(); inboxMessageRepo.save(m1)
        useCases.bulkAction(listOf(m1.id), "delete")
        assertNull(inboxMessageRepo.findById(m1.id))
    }

    @Test
    fun `savedReplies CRUD`() {
        val reply = useCases.createSavedReply(workspaceId, "Greeting", "Hello!", null)
        assertEquals("Greeting", reply.title)
        assertEquals(1, useCases.listSavedReplies(workspaceId).size)

        useCases.deleteSavedReply(reply.id)
        assertEquals(0, useCases.listSavedReplies(workspaceId).size)
    }

    @Test
    fun `SLA config save and retrieve`() {
        val config = InboxSLAConfig(UUID.randomUUID(), workspaceId, 30, true, false)
        val saved = useCases.updateSLAConfig(config)
        assertEquals(30, saved.targetResponseMinutes)

        val found = useCases.getSLAConfig(workspaceId)
        assertNotNull(found)
        assertEquals(30, found!!.targetResponseMinutes)
    }

    private fun createMessage(
        workspaceId: UUID = UUID.randomUUID(),
        status: InboxMessageStatus = InboxMessageStatus.UNREAD,
    ) = InboxMessage(
        id = UUID.randomUUID(),
        workspaceId = workspaceId,
        socialAccountId = UUID.randomUUID(),
        platformMessageId = "msg_${UUID.randomUUID()}",
        messageType = InboxMessageType.COMMENT,
        senderName = "Test",
        senderHandle = "@test",
        senderAvatarUrl = "",
        body = "Hello",
        sentiment = "NEUTRAL",
        sentimentSource = "auto",
        status = status,
        assignedTo = null,
        parentMessageId = null,
        relatedPostId = null,
        extra = null,
        receivedAt = Instant.now(),
        createdAt = Instant.now(),
    )

    class InMemInboxMessageRepo : InboxMessageRepository {
        private val items = mutableMapOf<UUID, InboxMessage>()
        override fun findById(id: UUID) = items[id]
        override fun findByWorkspaceId(workspaceId: UUID) = items.values.filter { it.workspaceId == workspaceId }
        override fun findByStatus(workspaceId: UUID, status: InboxMessageStatus) = items.values.filter { it.workspaceId == workspaceId && it.status == status }
        override fun findByAssignedTo(workspaceId: UUID, userId: UUID) = items.values.filter { it.workspaceId == workspaceId && it.assignedTo == userId }
        override fun findByPlatformMessageId(socialAccountId: UUID, platformMessageId: String) = items.values.find { it.socialAccountId == socialAccountId && it.platformMessageId == platformMessageId }
        override fun save(message: InboxMessage) = message.also { items[message.id] = it }
        override fun update(message: InboxMessage) = message.also { items[message.id] = it }
        override fun delete(id: UUID) { items.remove(id) }
    }

    class InMemInboxReplyRepo : InboxReplyRepository {
        private val items = mutableMapOf<UUID, InboxReply>()
        override fun findByMessageId(inboxMessageId: UUID) = items.values.filter { it.inboxMessageId == inboxMessageId }
        override fun save(reply: InboxReply) = reply.also { items[reply.id] = it }
        override fun delete(id: UUID) { items.remove(id) }
    }

    class InMemInternalNoteRepo : InternalNoteRepository {
        private val items = mutableMapOf<UUID, InternalNote>()
        override fun findByMessageId(inboxMessageId: UUID) = items.values.filter { it.inboxMessageId == inboxMessageId }
        override fun save(note: InternalNote) = note.also { items[note.id] = it }
        override fun delete(id: UUID) { items.remove(id) }
    }

    class InMemSavedReplyRepo : SavedReplyRepository {
        private val items = mutableMapOf<UUID, SavedReply>()
        override fun findByWorkspaceId(workspaceId: UUID) = items.values.filter { it.workspaceId == workspaceId }
        override fun save(reply: SavedReply) = reply.also { items[reply.id] = it }
        override fun update(reply: SavedReply) = reply.also { items[reply.id] = it }
        override fun delete(id: UUID) { items.remove(id) }
    }

    class InMemInboxSLAConfigRepo : InboxSLAConfigRepository {
        private val config = mutableMapOf<UUID, InboxSLAConfig>()
        override fun findByWorkspaceId(workspaceId: UUID) = config[workspaceId]
        override fun save(cfg: InboxSLAConfig) = cfg.also { config[cfg.workspaceId] = it }
        override fun update(cfg: InboxSLAConfig) = cfg.also { config[cfg.workspaceId] = it }
    }
}
