package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.NotificationPreference
import java.util.UUID

interface NotificationPreferenceRepository {
    fun findByUserId(userId: UUID): List<NotificationPreference>
    fun save(preference: NotificationPreference): NotificationPreference
    fun update(preference: NotificationPreference): NotificationPreference
}
