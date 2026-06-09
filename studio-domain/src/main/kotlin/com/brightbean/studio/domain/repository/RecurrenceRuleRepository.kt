package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.RecurrenceRule
import java.util.UUID

interface RecurrenceRuleRepository {
    fun findByPostId(postId: UUID): RecurrenceRule?
    fun findActive(): List<RecurrenceRule>
    fun save(rule: RecurrenceRule): RecurrenceRule
    fun update(rule: RecurrenceRule): RecurrenceRule
    fun delete(id: UUID)
}
