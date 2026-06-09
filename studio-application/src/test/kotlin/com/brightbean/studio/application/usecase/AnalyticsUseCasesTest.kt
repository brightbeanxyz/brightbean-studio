package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.AccountInsightsSnapshot
import com.brightbean.studio.domain.model.PostInsightsSnapshot
import com.brightbean.studio.domain.repository.AccountInsightsSnapshotRepository
import com.brightbean.studio.domain.repository.PostInsightsSnapshotRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

class AnalyticsUseCasesTest {

    private lateinit var accountRepo: InMemAccountInsightsSnapshotRepo
    private lateinit var postRepo: InMemPostInsightsSnapshotRepo
    private lateinit var useCases: AnalyticsUseCases

    @BeforeEach
    fun setUp() {
        accountRepo = InMemAccountInsightsSnapshotRepo()
        postRepo = InMemPostInsightsSnapshotRepo()
        useCases = AnalyticsUseCases(accountRepo, postRepo)
    }

    @Test
    fun `recordAccountSnapshot saves snapshot`() {
        val socialAccountId = UUID.randomUUID()
        val date = LocalDate.now()
        val snapshot = useCases.recordAccountSnapshot(socialAccountId, "followers", date, 1500.0)
        assertEquals(socialAccountId, snapshot.socialAccountId)
        assertEquals("followers", snapshot.metricKey)
        assertEquals(1500.0, snapshot.value)
    }

    @Test
    fun `recordAccountSnapshot upserts on conflict`() {
        val socialAccountId = UUID.randomUUID()
        val date = LocalDate.now()
        useCases.recordAccountSnapshot(socialAccountId, "followers", date, 1500.0)
        val updated = useCases.recordAccountSnapshot(socialAccountId, "followers", date, 1600.0)
        assertEquals(1600.0, updated.value)
        assertEquals(1, accountRepo.data.size)
    }

    @Test
    fun `recordPostSnapshot saves snapshot`() {
        val platformPostId = UUID.randomUUID()
        val date = LocalDate.now()
        val snapshot = useCases.recordPostSnapshot(platformPostId, "likes", date, 42.0)
        assertEquals(platformPostId, snapshot.platformPostId)
        assertEquals("likes", snapshot.metricKey)
        assertEquals(42.0, snapshot.value)
    }

    @Test
    fun `getAccountSeries returns filtered metrics`() {
        val socialAccountId = UUID.randomUUID()
        val today = LocalDate.now()
        useCases.recordAccountSnapshot(socialAccountId, "followers", today, 100.0)
        useCases.recordAccountSnapshot(socialAccountId, "impressions", today, 500.0)
        useCases.recordAccountSnapshot(socialAccountId, "followers", today.minusDays(1), 90.0)

        val series = useCases.getAccountSeries(socialAccountId, "followers", 7)
        assertEquals(2, series.size)
        series.forEach { assertEquals("followers", it.metricKey) }
    }

    @Test
    fun `getPostMetrics returns latest value per metric`() {
        val postId = UUID.randomUUID()
        val today = LocalDate.now()
        useCases.recordPostSnapshot(postId, "likes", today.minusDays(2), 10.0)
        useCases.recordPostSnapshot(postId, "likes", today, 20.0)
        useCases.recordPostSnapshot(postId, "comments", today, 5.0)

        val metrics = useCases.getPostMetrics(postId)
        assertEquals(20.0, metrics["likes"])
        assertEquals(5.0, metrics["comments"])
    }

    @Test
    fun `getAccountKpiCards computes derived KPIs`() {
        val socialAccountId = UUID.randomUUID()
        val today = LocalDate.now()
        useCases.recordAccountSnapshot(socialAccountId, "followers", today.minusDays(2), 100.0)
        useCases.recordAccountSnapshot(socialAccountId, "followers", today, 120.0)
        useCases.recordAccountSnapshot(socialAccountId, "impressions", today, 500.0)
        useCases.recordAccountSnapshot(socialAccountId, "engagement_rate", today, 4.5)

        val kpis = useCases.getAccountKpiCards(socialAccountId, 7)
        assertEquals(120.0, kpis["followers"])
        assertTrue(kpis["followerGrowth"] as Double > 0)
        assertEquals(500.0, kpis["totalImpressions"])
        assertEquals(4.5, kpis["avgEngagementRate"])
    }

    class InMemAccountInsightsSnapshotRepo : AccountInsightsSnapshotRepository {
        val data = mutableMapOf<String, AccountInsightsSnapshot>()

        override fun findBySocialAccountAndDateRange(socialAccountId: UUID, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshot> =
            data.values.filter { it.socialAccountId == socialAccountId && !it.date.isBefore(from) && !it.date.isAfter(to) }

        override fun findBySocialAccountAndMetricKeyAndDateRange(socialAccountId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshot> =
            data.values.filter { it.socialAccountId == socialAccountId && it.metricKey == metricKey && !it.date.isBefore(from) && !it.date.isAfter(to) }

        override fun save(snapshot: AccountInsightsSnapshot): AccountInsightsSnapshot {
            val key = "${snapshot.socialAccountId}:${snapshot.metricKey}:${snapshot.date}"
            data[key] = snapshot
            return snapshot
        }
    }

    class InMemPostInsightsSnapshotRepo : PostInsightsSnapshotRepository {
        val data = mutableMapOf<String, PostInsightsSnapshot>()

        override fun findByPlatformPostAndDateRange(platformPostId: UUID, from: LocalDate, to: LocalDate): List<PostInsightsSnapshot> =
            data.values.filter { it.platformPostId == platformPostId && !it.date.isBefore(from) && !it.date.isAfter(to) }

        override fun findByPlatformPostAndMetricKeyAndDateRange(platformPostId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<PostInsightsSnapshot> =
            data.values.filter { it.platformPostId == platformPostId && it.metricKey == metricKey && !it.date.isBefore(from) && !it.date.isAfter(to) }

        override fun save(snapshot: PostInsightsSnapshot): PostInsightsSnapshot {
            val key = "${snapshot.platformPostId}:${snapshot.metricKey}:${snapshot.date}"
            data[key] = snapshot
            return snapshot
        }
    }
}
