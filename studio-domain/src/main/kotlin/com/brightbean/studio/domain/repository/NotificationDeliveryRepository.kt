package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.NotificationDelivery
import java.util.UUID

interface NotificationDeliveryRepository {
    fun findByNotificationId(notificationId: UUID): List<NotificationDelivery>
    fun save(delivery: NotificationDelivery): NotificationDelivery
    fun update(delivery: NotificationDelivery): NotificationDelivery
    fun findPending(): List<NotificationDelivery>
}
