package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate

@RegisterKotlinMapper(AnalyticsPlatformConfigDto::class)
interface AnalyticsPlatformConfigDao {
    @SqlQuery("SELECT * FROM analytics_platform_config WHERE platform = :platform")
    fun findByPlatform(platform: String): AnalyticsPlatformConfigDto?

    @SqlQuery("SELECT * FROM analytics_platform_config")
    fun findAll(): List<AnalyticsPlatformConfigDto>

    @SqlUpdate("""
        INSERT INTO analytics_platform_config (platform, is_enabled, updated_at)
        VALUES (:dto.platform, :dto.isEnabled, :dto.updatedAt)
    """)
    fun insert(dto: AnalyticsPlatformConfigDto)

    @SqlUpdate("""
        UPDATE analytics_platform_config SET
            is_enabled = :dto.isEnabled,
            updated_at = :dto.updatedAt
        WHERE platform = :dto.platform
    """)
    fun update(dto: AnalyticsPlatformConfigDto)
}

data class AnalyticsPlatformConfigDto(
    val platform: String,
    val isEnabled: Boolean,
    val updatedAt: java.time.Instant,
)
