package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PostInsightsSnapshot
import java.time.LocalDate
import java.util.UUID

interface PostInsightsSnapshotRepository {
    fun findByPlatformPostAndDateRange(platformPostId: UUID, from: LocalDate, to: LocalDate): List<PostInsightsSnapshot>
    fun findByPlatformPostAndMetricKeyAndDateRange(platformPostId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<PostInsightsSnapshot>
    fun save(snapshot: PostInsightsSnapshot): PostInsightsSnapshot
}
