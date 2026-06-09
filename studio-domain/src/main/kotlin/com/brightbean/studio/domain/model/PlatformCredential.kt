package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class TestResult {
    SUCCESS,
    FAILURE,
    UNTESTED,
}

data class PlatformCredential(
    val id: UUID,
    val organizationId: UUID,
    val platform: String,
    val credentials: String,
    val isConfigured: Boolean = false,
    val testedAt: Instant? = null,
    val testResult: TestResult = TestResult.UNTESTED,
    val createdAt: Instant,
    val updatedAt: Instant,
)
