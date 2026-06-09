package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ApprovalReminder
import java.util.UUID

interface ApprovalReminderRepository {
    fun findByPostId(postId: UUID): ApprovalReminder?
    fun save(reminder: ApprovalReminder): ApprovalReminder
    fun update(reminder: ApprovalReminder): ApprovalReminder
}
