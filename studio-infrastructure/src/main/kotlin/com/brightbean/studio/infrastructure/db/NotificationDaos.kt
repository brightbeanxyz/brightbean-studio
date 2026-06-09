package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.time.LocalTime
import java.util.UUID

@RegisterKotlinMapper(NotificationDto::class)
interface NotificationDao {
    @SqlQuery("SELECT * FROM notifications_notification WHERE id = :id")
    fun findById(id: UUID): NotificationDto?

    @SqlQuery("SELECT * FROM notifications_notification WHERE user_id = :userId ORDER BY created_at DESC")
    fun findByUserId(userId: UUID): List<NotificationDto>

    @SqlQuery("SELECT * FROM notifications_notification WHERE user_id = :userId AND is_read = false ORDER BY created_at DESC")
    fun findUnreadByUserId(userId: UUID): List<NotificationDto>

    @SqlQuery("SELECT COUNT(*) FROM notifications_notification WHERE user_id = :userId AND is_read = false")
    fun countUnreadByUserId(userId: UUID): Int

    @SqlUpdate("""
        INSERT INTO notifications_notification (id, user_id, event_type, title, body, data, is_read, read_at, created_at)
        VALUES (:dto.id, :dto.userId, :dto.eventType, :dto.title, :dto.body, :dto.data, :dto.isRead, :dto.readAt, :dto.createdAt)
    """)
    fun insert(dto: NotificationDto)

    @SqlUpdate("""
        UPDATE notifications_notification SET is_read = :dto.isRead, read_at = :dto.readAt
        WHERE id = :dto.id
    """)
    fun update(dto: NotificationDto)

    @SqlUpdate("UPDATE notifications_notification SET is_read = true, read_at = NOW() WHERE user_id = :userId AND is_read = false")
    fun markAllReadByUserId(userId: UUID)
}

data class NotificationDto(
    val id: UUID,
    val userId: UUID,
    val eventType: String,
    val title: String,
    val body: String,
    val data: String?,
    val isRead: Boolean,
    val readAt: Instant?,
    val createdAt: Instant,
)

@RegisterKotlinMapper(NotificationPreferenceDto::class)
interface NotificationPreferenceDao {
    @SqlQuery("SELECT * FROM notifications_preference WHERE user_id = :userId")
    fun findByUserId(userId: UUID): List<NotificationPreferenceDto>

    @SqlUpdate("""
        INSERT INTO notifications_preference (id, user_id, event_type, channel, is_enabled)
        VALUES (:dto.id, :dto.userId, :dto.eventType, :dto.channel, :dto.isEnabled)
    """)
    fun insert(dto: NotificationPreferenceDto)

    @SqlUpdate("""
        UPDATE notifications_preference SET is_enabled = :dto.isEnabled
        WHERE id = :dto.id
    """)
    fun update(dto: NotificationPreferenceDto)
}

data class NotificationPreferenceDto(
    val id: UUID,
    val userId: UUID,
    val eventType: String,
    val channel: String,
    val isEnabled: Boolean,
)

@RegisterKotlinMapper(NotificationDeliveryDto::class)
interface NotificationDeliveryDao {
    @SqlQuery("SELECT * FROM notifications_delivery WHERE notification_id = :notificationId")
    fun findByNotificationId(notificationId: UUID): List<NotificationDeliveryDto>

    @SqlQuery("SELECT * FROM notifications_delivery WHERE status = 'PENDING'")
    fun findPending(): List<NotificationDeliveryDto>

    @SqlUpdate("""
        INSERT INTO notifications_delivery (id, notification_id, channel, status, error_message, delivered_at, attempts, next_retry_at, created_at)
        VALUES (:dto.id, :dto.notificationId, :dto.channel, :dto.status, :dto.errorMessage, :dto.deliveredAt, :dto.attempts, :dto.nextRetryAt, :dto.createdAt)
    """)
    fun insert(dto: NotificationDeliveryDto)

    @SqlUpdate("""
        UPDATE notifications_delivery SET status = :dto.status, error_message = :dto.errorMessage, delivered_at = :dto.deliveredAt, attempts = :dto.attempts, next_retry_at = :dto.nextRetryAt
        WHERE id = :dto.id
    """)
    fun update(dto: NotificationDeliveryDto)
}

data class NotificationDeliveryDto(
    val id: UUID,
    val notificationId: UUID,
    val channel: String,
    val status: String,
    val errorMessage: String,
    val deliveredAt: Instant?,
    val attempts: Int,
    val nextRetryAt: Instant?,
    val createdAt: Instant,
)

@RegisterKotlinMapper(QuietHoursDto::class)
interface QuietHoursDao {
    @SqlQuery("SELECT * FROM notifications_quiet_hours WHERE user_id = :userId")
    fun findByUserId(userId: UUID): QuietHoursDto?

    @SqlUpdate("""
        INSERT INTO notifications_quiet_hours (id, user_id, is_enabled, start_time, end_time, timezone, digest_mode)
        VALUES (:dto.id, :dto.userId, :dto.isEnabled, :dto.startTime, :dto.endTime, :dto.timezone, :dto.digestMode)
    """)
    fun insert(dto: QuietHoursDto)

    @SqlUpdate("""
        UPDATE notifications_quiet_hours SET is_enabled = :dto.isEnabled, start_time = :dto.startTime, end_time = :dto.endTime, timezone = :dto.timezone, digest_mode = :dto.digestMode
        WHERE id = :dto.id
    """)
    fun update(dto: QuietHoursDto)
}

data class QuietHoursDto(
    val id: UUID,
    val userId: UUID,
    val isEnabled: Boolean,
    val startTime: LocalTime?,
    val endTime: LocalTime?,
    val timezone: String,
    val digestMode: Boolean,
)
