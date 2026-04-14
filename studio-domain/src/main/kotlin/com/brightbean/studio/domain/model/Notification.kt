package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class Notification(
    val id: UUID,
    val workspaceId: UUID,
    val userId: UUID,
    val type: NotificationType,
    val title: String,
    val message: String,
    val metadata: Map<String, String>,
    val isRead: Boolean,
    val createdAt: Instant,
)
