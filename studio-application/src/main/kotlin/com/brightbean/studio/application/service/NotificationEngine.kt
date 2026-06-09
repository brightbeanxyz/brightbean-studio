package com.brightbean.studio.application.service

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
import java.time.Instant
import java.util.UUID

class NotificationEngine(
    private val notificationRepository: NotificationRepository,
    private val notificationPreferenceRepository: NotificationPreferenceRepository,
    private val notificationDeliveryRepository: NotificationDeliveryRepository,
    private val quietHoursRepository: QuietHoursRepository,
) {
    fun notify(userId: UUID, eventType: EventType, title: String, body: String, data: String? = null): Notification {
        val notification = Notification(
            id = UUID.randomUUID(),
            userId = userId,
            eventType = eventType,
            title = title,
            body = body,
            data = data,
            isRead = false,
            readAt = null,
            createdAt = Instant.now(),
        )
        notificationRepository.save(notification)

        val preferences = notificationPreferenceRepository.findByUserId(userId)
        val channels = if (preferences.isEmpty()) listOf(NotificationChannel.IN_APP) else preferences.filter { it.isEnabled }.map { it.channel }

        for (channel in channels) {
            notificationDeliveryRepository.save(
                NotificationDelivery(
                    id = UUID.randomUUID(),
                    notificationId = notification.id,
                    channel = channel,
                    status = DeliveryStatus.PENDING,
                    errorMessage = "",
                    deliveredAt = null,
                    attempts = 0,
                    nextRetryAt = null,
                    createdAt = Instant.now(),
                )
            )
        }

        return notification
    }

    fun sendInvitation(email: String, workspaceId: UUID, inviterId: UUID) {
        notify(inviterId, EventType.TEAM_MEMBER_INVITED, "Invitation sent", "Invitation sent to $email")
    }
}

class NotificationUseCases(
    private val notificationRepository: NotificationRepository,
    private val notificationPreferenceRepository: NotificationPreferenceRepository,
    private val quietHoursRepository: QuietHoursRepository,
) {
    fun listByUser(userId: UUID): List<Notification> = notificationRepository.findByUserId(userId)
    fun markAsRead(notificationId: UUID): Notification? {
        val n = notificationRepository.findById(notificationId) ?: return null
        return notificationRepository.update(n.copy(isRead = true, readAt = Instant.now()))
    }
    fun markAllRead(userId: UUID) = notificationRepository.markAllReadByUserId(userId)
    fun getUnreadCount(userId: UUID): Int = notificationRepository.countUnreadByUserId(userId)
    fun getPreferences(userId: UUID): List<NotificationPreference> = notificationPreferenceRepository.findByUserId(userId)
    fun updatePreference(preference: NotificationPreference): NotificationPreference = notificationPreferenceRepository.update(preference)
    fun getQuietHours(userId: UUID): QuietHours? = quietHoursRepository.findByUserId(userId)
    fun updateQuietHours(quietHours: QuietHours): QuietHours =
        if (quietHoursRepository.findByUserId(quietHours.userId) == null) quietHoursRepository.save(quietHours)
        else quietHoursRepository.update(quietHours)
}
