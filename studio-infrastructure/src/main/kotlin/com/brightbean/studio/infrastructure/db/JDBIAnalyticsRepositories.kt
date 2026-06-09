package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.AccountInsightsSnapshot
import com.brightbean.studio.domain.model.PostInsightsSnapshot
import com.brightbean.studio.domain.repository.AccountInsightsSnapshotRepository
import com.brightbean.studio.domain.repository.PostInsightsSnapshotRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.time.LocalDate
import java.util.UUID

class JDBIAccountInsightsSnapshotRepository(jdbi: Jdbi) : AccountInsightsSnapshotRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: AccountInsightsSnapshotDao by lazy { jdbi.onDemand(AccountInsightsSnapshotDao::class.java) }

    override fun findBySocialAccountAndDateRange(socialAccountId: UUID, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshot> =
        dao.findBySocialAccountAndDateRange(socialAccountId, from, to).map { it.toDomain() }

    override fun findBySocialAccountAndMetricKeyAndDateRange(socialAccountId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshot> =
        dao.findBySocialAccountAndMetricKeyAndDateRange(socialAccountId, metricKey, from, to).map { it.toDomain() }

    override fun save(snapshot: AccountInsightsSnapshot): AccountInsightsSnapshot {
        dao.upsert(snapshot.toDto())
        return snapshot
    }

    private fun AccountInsightsSnapshot.toDto() = AccountInsightsSnapshotDto(id, socialAccountId, metricKey, date, value, capturedAt)
    private fun AccountInsightsSnapshotDto.toDomain() = AccountInsightsSnapshot(id, socialAccountId, metricKey, date, value, capturedAt)
}

class JDBIPostInsightsSnapshotRepository(jdbi: Jdbi) : PostInsightsSnapshotRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: PostInsightsSnapshotDao by lazy { jdbi.onDemand(PostInsightsSnapshotDao::class.java) }

    override fun findByPlatformPostAndDateRange(platformPostId: UUID, from: LocalDate, to: LocalDate): List<PostInsightsSnapshot> =
        dao.findByPlatformPostAndDateRange(platformPostId, from, to).map { it.toDomain() }

    override fun findByPlatformPostAndMetricKeyAndDateRange(platformPostId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<PostInsightsSnapshot> =
        dao.findByPlatformPostAndMetricKeyAndDateRange(platformPostId, metricKey, from, to).map { it.toDomain() }

    override fun save(snapshot: PostInsightsSnapshot): PostInsightsSnapshot {
        dao.upsert(snapshot.toDto())
        return snapshot
    }

    private fun PostInsightsSnapshot.toDto() = PostInsightsSnapshotDto(id, platformPostId, metricKey, date, value, capturedAt)
    private fun PostInsightsSnapshotDto.toDomain() = PostInsightsSnapshot(id, platformPostId, metricKey, date, value, capturedAt)
}
