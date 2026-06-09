package com.brightbean.studio.domain.model

import java.time.Instant
import java.time.LocalTime
import java.util.UUID

enum class EventType {
    POST_SUBMITTED, POST_APPROVED, POST_CHANGES_REQUESTED, POST_REJECTED,
    POST_PUBLISHED, POST_FAILED, NEW_INBOX_MESSAGE, INBOX_SLA_OVERDUE,
    CLIENT_APPROVAL_REQUESTED, TEAM_MEMBER_INVITED, SOCIAL_ACCOUNT_DISCONNECTED,
    REPORT_GENERATED, ENGAGEMENT_ALERT, COMMENT_MENTION, APPROVAL_REMINDER,
    APPROVAL_STALLED, CLIENT_CONNECTED_ACCOUNTS
}

enum class NotificationChannel { IN_APP, EMAIL, WEBHOOK }
enum class DeliveryStatus { PENDING, DELIVERED, FAILED }

data class Notification(
    val id: UUID,
    val userId: UUID,
    val eventType: EventType,
    val title: String,
    val body: String,
    val data: String?,
    val isRead: Boolean,
    val readAt: Instant?,
    val createdAt: Instant,
)

data class NotificationPreference(
    val id: UUID,
    val userId: UUID,
    val eventType: EventType,
    val channel: NotificationChannel,
    val isEnabled: Boolean,
)

data class NotificationDelivery(
    val id: UUID,
    val notificationId: UUID,
    val channel: NotificationChannel,
    val status: DeliveryStatus,
    val errorMessage: String,
    val deliveredAt: Instant?,
    val attempts: Int,
    val nextRetryAt: Instant?,
    val createdAt: Instant,
)

data class QuietHours(
    val id: UUID,
    val userId: UUID,
    val isEnabled: Boolean,
    val startTime: LocalTime?,
    val endTime: LocalTime?,
    val timezone: String,
    val digestMode: Boolean,
)
