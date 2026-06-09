package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class InboxMessageTest {

    @Test
    fun `inbox messages can be filtered by status`() {
        val messages = listOf(
            createInboxMessage(status = InboxMessageStatus.UNREAD),
            createInboxMessage(status = InboxMessageStatus.OPEN),
            createInboxMessage(status = InboxMessageStatus.UNREAD),
            createInboxMessage(status = InboxMessageStatus.RESOLVED),
        )

        val unreadMessages = messages.filter { it.status == InboxMessageStatus.UNREAD }
        assertEquals(2, unreadMessages.size)
    }

    @Test
    fun `inbox messages can be filtered by type`() {
        val messages = listOf(
            createInboxMessage(messageType = InboxMessageType.COMMENT),
            createInboxMessage(messageType = InboxMessageType.DM),
            createInboxMessage(messageType = InboxMessageType.COMMENT),
            createInboxMessage(messageType = InboxMessageType.MENTION),
        )

        val comments = messages.filter { it.messageType == InboxMessageType.COMMENT }
        assertEquals(2, comments.size)
    }

    @Test
    fun `unread messages should have UNREAD status`() {
        val message = createInboxMessage(status = InboxMessageStatus.UNREAD)
        assertTrue(message.status == InboxMessageStatus.UNREAD)
    }

    @Test
    fun `open messages should have OPEN status`() {
        val message = createInboxMessage(status = InboxMessageStatus.OPEN)
        assertTrue(message.status == InboxMessageStatus.OPEN)
    }

    private fun createInboxMessage(
        id: UUID = UUID.randomUUID(),
        messageType: InboxMessageType = InboxMessageType.COMMENT,
        status: InboxMessageStatus = InboxMessageStatus.UNREAD,
    ): InboxMessage {
        return InboxMessage(
            id = id,
            workspaceId = UUID.randomUUID(),
            socialAccountId = UUID.randomUUID(),
            platformMessageId = "platform-msg-${id}",
            messageType = messageType,
            senderName = "Test Sender",
            senderHandle = "@testsender",
            senderAvatarUrl = "",
            body = "Test content",
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
    }
}
