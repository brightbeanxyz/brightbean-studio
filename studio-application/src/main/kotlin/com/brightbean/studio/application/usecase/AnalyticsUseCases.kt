package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.AccountInsightsSnapshot
import com.brightbean.studio.domain.model.PostInsightsSnapshot
import com.brightbean.studio.domain.repository.AccountInsightsSnapshotRepository
import com.brightbean.studio.domain.repository.PostInsightsSnapshotRepository
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

class AnalyticsUseCases(
    private val accountSnapshotRepo: AccountInsightsSnapshotRepository,
    private val postSnapshotRepo: PostInsightsSnapshotRepository,
) {
    fun recordAccountSnapshot(socialAccountId: UUID, metricKey: String, date: LocalDate, value: Double): AccountInsightsSnapshot {
        val snapshot = AccountInsightsSnapshot(
            id = UUID.randomUUID(),
            socialAccountId = socialAccountId,
            metricKey = metricKey,
            date = date,
            value = value,
            capturedAt = Instant.now(),
        )
        return accountSnapshotRepo.save(snapshot)
    }

    fun recordPostSnapshot(platformPostId: UUID, metricKey: String, date: LocalDate, value: Double): PostInsightsSnapshot {
        val snapshot = PostInsightsSnapshot(
            id = UUID.randomUUID(),
            platformPostId = platformPostId,
            metricKey = metricKey,
            date = date,
            value = value,
            capturedAt = Instant.now(),
        )
        return postSnapshotRepo.save(snapshot)
    }

    fun getAccountSeries(socialAccountId: UUID, metricKey: String, days: Int): List<AccountInsightsSnapshot> {
        val to = LocalDate.now()
        val from = to.minusDays(days.toLong())
        return accountSnapshotRepo.findBySocialAccountAndMetricKeyAndDateRange(socialAccountId, metricKey, from, to)
    }

    fun getPostMetrics(platformPostId: UUID): Map<String, Double> {
        val to = LocalDate.now()
        val from = to.minusDays(90)
        val snapshots = postSnapshotRepo.findByPlatformPostAndDateRange(platformPostId, from, to)
        return snapshots.groupBy { it.metricKey }
            .mapValues { entry -> entry.value.maxByOrNull { it.date }?.value ?: 0.0 }
    }

    fun getAccountKpiCards(socialAccountId: UUID, days: Int): Map<String, Any> {
        val to = LocalDate.now()
        val from = to.minusDays(days.toLong())
        val snapshots = accountSnapshotRepo.findBySocialAccountAndDateRange(socialAccountId, from, to)

        val followers = snapshots.filter { it.metricKey == "followers" }.sortedBy { it.date }
        val impressions = snapshots.filter { it.metricKey == "impressions" }
        val engagementRate = snapshots.filter { it.metricKey == "engagement_rate" }

        val currentFollowers = followers.lastOrNull()?.value ?: 0.0
        val previousFollowers = followers.firstOrNull()?.value ?: 0.0
        val followerGrowth = if (previousFollowers > 0) ((currentFollowers - previousFollowers) / previousFollowers) * 100 else 0.0

        val totalImpressions = impressions.sumOf { it.value }
        val avgEngagement = if (engagementRate.isNotEmpty()) engagementRate.map { it.value }.average() else 0.0

        return mapOf(
            "followers" to currentFollowers,
            "followerGrowth" to followerGrowth,
            "totalImpressions" to totalImpressions,
            "avgEngagementRate" to avgEngagement,
            "days" to days,
        )
    }
}
