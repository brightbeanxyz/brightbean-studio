package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class InboxItem(
    val id: UUID,
    val workspaceId: UUID,
    val socialAccountId: UUID,
    val platformType: PlatformType,
    val platformItemId: String,
    val type: InboxItemType,
    val content: String,
    val authorName: String,
    val authorAvatarUrl: String?,
    val mediaUrls: List<String>,
    val sentiment: Sentiment?,
    val isRead: Boolean,
    val isArchived: Boolean,
    val platformCreatedAt: Instant,
    val receivedAt: Instant,
)
