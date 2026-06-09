package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.DeliveryStatus
import com.brightbean.studio.domain.model.EventType
import com.brightbean.studio.domain.model.Notification
import com.brightbean.studio.domain.model.NotificationChannel
import com.brightbean.studio.domain.model.NotificationDelivery
import com.brightbean.studio.domain.model.NotificationPreference
import com.brightbean.studio.domain.model.QuietHours
import com.brightbean.studio.domain.repository.NotificationDeliveryRepository
import com.brightbean.studio.domain.repository.NotificationPreferenceRepository
import com.brightbean.studio.domain.repository.NotificationRepository
import com.brightbean.studio.domain.repository.QuietHoursRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBINotificationRepository(jdbi: Jdbi) : NotificationRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: NotificationDao by lazy { jdbi.onDemand(NotificationDao::class.java) }

    override fun findById(id: UUID): Notification? = dao.findById(id)?.toDomain()
    override fun findByUserId(userId: UUID): List<Notification> = dao.findByUserId(userId).map { it.toDomain() }
    override fun findUnreadByUserId(userId: UUID): List<Notification> = dao.findUnreadByUserId(userId).map { it.toDomain() }
    override fun countUnreadByUserId(userId: UUID): Int = dao.countUnreadByUserId(userId)
    override fun save(notification: Notification): Notification { dao.insert(notification.toDto()); return notification }
    override fun update(notification: Notification): Notification { dao.update(notification.toDto()); return notification }
    override fun markAllReadByUserId(userId: UUID) = dao.markAllReadByUserId(userId)

    private fun Notification.toDto() = NotificationDto(id, userId, eventType.name, title, body, data, isRead, readAt, createdAt)
    private fun NotificationDto.toDomain() = Notification(id, userId, EventType.valueOf(eventType), title, body, data, isRead, readAt, createdAt)
}

class JDBINotificationPreferenceRepository(jdbi: Jdbi) : NotificationPreferenceRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: NotificationPreferenceDao by lazy { jdbi.onDemand(NotificationPreferenceDao::class.java) }

    override fun findByUserId(userId: UUID): List<NotificationPreference> = dao.findByUserId(userId).map { it.toDomain() }
    override fun save(preference: NotificationPreference): NotificationPreference { dao.insert(preference.toDto()); return preference }
    override fun update(preference: NotificationPreference): NotificationPreference { dao.update(preference.toDto()); return preference }

    private fun NotificationPreference.toDto() = NotificationPreferenceDto(id, userId, eventType.name, channel.name, isEnabled)
    private fun NotificationPreferenceDto.toDomain() = NotificationPreference(id, userId, EventType.valueOf(eventType), NotificationChannel.valueOf(channel), isEnabled)
}

class JDBINotificationDeliveryRepository(jdbi: Jdbi) : NotificationDeliveryRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: NotificationDeliveryDao by lazy { jdbi.onDemand(NotificationDeliveryDao::class.java) }

    override fun findByNotificationId(notificationId: UUID): List<NotificationDelivery> = dao.findByNotificationId(notificationId).map { it.toDomain() }
    override fun save(delivery: NotificationDelivery): NotificationDelivery { dao.insert(delivery.toDto()); return delivery }
    override fun update(delivery: NotificationDelivery): NotificationDelivery { dao.update(delivery.toDto()); return delivery }
    override fun findPending(): List<NotificationDelivery> = dao.findPending().map { it.toDomain() }

    private fun NotificationDelivery.toDto() = NotificationDeliveryDto(id, notificationId, channel.name, status.name, errorMessage, deliveredAt, attempts, nextRetryAt, createdAt)
    private fun NotificationDeliveryDto.toDomain() = NotificationDelivery(id, notificationId, NotificationChannel.valueOf(channel), DeliveryStatus.valueOf(status), errorMessage, deliveredAt, attempts, nextRetryAt, createdAt)
}

class JDBIQuietHoursRepository(jdbi: Jdbi) : QuietHoursRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: QuietHoursDao by lazy { jdbi.onDemand(QuietHoursDao::class.java) }

    override fun findByUserId(userId: UUID): QuietHours? = dao.findByUserId(userId)?.toDomain()
    override fun save(quietHours: QuietHours): QuietHours { dao.insert(quietHours.toDto()); return quietHours }
    override fun update(quietHours: QuietHours): QuietHours { dao.update(quietHours.toDto()); return quietHours }

    private fun QuietHours.toDto() = QuietHoursDto(id, userId, isEnabled, startTime, endTime, timezone, digestMode)
    private fun QuietHoursDto.toDomain() = QuietHours(id, userId, isEnabled, startTime, endTime, timezone, digestMode)
}
