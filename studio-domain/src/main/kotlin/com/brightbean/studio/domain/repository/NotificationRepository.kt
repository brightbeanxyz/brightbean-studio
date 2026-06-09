package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Notification
import java.util.UUID

interface NotificationRepository {
    fun findById(id: UUID): Notification?
    fun findByUserId(userId: UUID): List<Notification>
    fun findUnreadByUserId(userId: UUID): List<Notification>
    fun countUnreadByUserId(userId: UUID): Int
    fun save(notification: Notification): Notification
    fun update(notification: Notification): Notification
    fun markAllReadByUserId(userId: UUID)
}
