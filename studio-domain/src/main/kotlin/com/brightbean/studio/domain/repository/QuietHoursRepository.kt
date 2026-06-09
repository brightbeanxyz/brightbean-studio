package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.QuietHours
import java.util.UUID

interface QuietHoursRepository {
    fun findByUserId(userId: UUID): QuietHours?
    fun save(quietHours: QuietHours): QuietHours
    fun update(quietHours: QuietHours): QuietHours
}
