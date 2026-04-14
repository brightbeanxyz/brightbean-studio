package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class InboxItemTest {

    @Test
    fun `inbox items can be filtered by platform`() {
        val items = listOf(
            createInboxItem(platformType = PlatformType.FACEBOOK),
            createInboxItem(platformType = PlatformType.INSTAGRAM),
            createInboxItem(platformType = PlatformType.FACEBOOK),
            createInboxItem(platformType = PlatformType.LINKEDIN_COMPANY),
        )

        val facebookItems = items.filter { it.platformType == PlatformType.FACEBOOK }
        assertEquals(2, facebookItems.size)
    }

    @Test
    fun `inbox items can be filtered by read status`() {
        val items = listOf(
            createInboxItem(isRead = false),
            createInboxItem(isRead = true),
            createInboxItem(isRead = false),
            createInboxItem(isRead = true),
        )

        val unreadItems = items.filter { !it.isRead }
        val readItems = items.filter { it.isRead }

        assertEquals(2, unreadItems.size)
        assertEquals(2, readItems.size)
    }

    @Test
    fun `unread items should not be marked as read`() {
        val item = createInboxItem(isRead = false)
        assertFalse(item.isRead)
    }

    @Test
    fun `read items should be marked as read`() {
        val item = createInboxItem(isRead = true)
        assertTrue(item.isRead)
    }

    private fun createInboxItem(
        id: UUID = UUID.randomUUID(),
        platformType: PlatformType = PlatformType.FACEBOOK,
        isRead: Boolean = false,
    ): InboxItem {
        return InboxItem(
            id = id,
            workspaceId = UUID.randomUUID(),
            socialAccountId = UUID.randomUUID(),
            platformType = platformType,
            platformItemId = "platform-item-1",
            type = InboxItemType.COMMENT,
            content = "Test content",
            authorName = "Test Author",
            authorAvatarUrl = null,
            mediaUrls = emptyList(),
            sentiment = Sentiment.NEUTRAL,
            isRead = isRead,
            isArchived = false,
            platformCreatedAt = Instant.now(),
            receivedAt = Instant.now(),
        )
    }
}
