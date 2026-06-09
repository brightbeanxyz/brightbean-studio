package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.RecurrenceFrequency
import com.brightbean.studio.domain.model.RecurrenceRule
import com.brightbean.studio.domain.repository.RecurrenceRuleRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIRecurrenceRuleRepository(jdbi: Jdbi) : RecurrenceRuleRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: RecurrenceRuleDao by lazy { jdbi.onDemand(RecurrenceRuleDao::class.java) }

    override fun findByPostId(postId: UUID): RecurrenceRule? = dao.findByPostId(postId)?.toDomain()

    override fun findActive(): List<RecurrenceRule> = dao.findActive().map { it.toDomain() }

    override fun save(rule: RecurrenceRule): RecurrenceRule {
        dao.insert(rule.toDto())
        return rule
    }

    override fun update(rule: RecurrenceRule): RecurrenceRule {
        dao.update(rule.toDto())
        return rule
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun RecurrenceRule.toDto() = RecurrenceRuleDto(
        id = id, postId = postId, frequency = frequency.name,
        intervalDays = interval, endDate = endDate,
        lastGeneratedAt = lastGeneratedAt, isActive = isActive, createdAt = createdAt,
    )

    private fun RecurrenceRuleDto.toDomain() = RecurrenceRule(
        id = id, postId = postId,
        frequency = try { RecurrenceFrequency.valueOf(frequency) } catch (_: Exception) { RecurrenceFrequency.DAILY },
        interval = intervalDays, endDate = endDate,
        lastGeneratedAt = lastGeneratedAt, isActive = isActive, createdAt = createdAt,
    )
}
