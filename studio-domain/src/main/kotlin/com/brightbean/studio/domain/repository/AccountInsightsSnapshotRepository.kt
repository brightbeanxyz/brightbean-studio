package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.AccountInsightsSnapshot
import java.time.LocalDate
import java.util.UUID

interface AccountInsightsSnapshotRepository {
    fun findBySocialAccountAndDateRange(socialAccountId: UUID, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshot>
    fun findBySocialAccountAndMetricKeyAndDateRange(socialAccountId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshot>
    fun save(snapshot: AccountInsightsSnapshot): AccountInsightsSnapshot
}
