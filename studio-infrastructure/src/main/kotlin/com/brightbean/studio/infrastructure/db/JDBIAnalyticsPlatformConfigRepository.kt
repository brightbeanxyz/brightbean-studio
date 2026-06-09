package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.AnalyticsPlatformConfig
import com.brightbean.studio.domain.repository.AnalyticsPlatformConfigRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin

class JDBIAnalyticsPlatformConfigRepository(jdbi: Jdbi) : AnalyticsPlatformConfigRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: AnalyticsPlatformConfigDao by lazy { jdbi.onDemand(AnalyticsPlatformConfigDao::class.java) }

    override fun findByPlatform(platform: String): AnalyticsPlatformConfig? =
        dao.findByPlatform(platform)?.toDomain()

    override fun findAll(): List<AnalyticsPlatformConfig> =
        dao.findAll().map { it.toDomain() }

    override fun save(config: AnalyticsPlatformConfig): AnalyticsPlatformConfig {
        dao.insert(config.toDto())
        return config
    }

    override fun update(config: AnalyticsPlatformConfig): AnalyticsPlatformConfig {
        dao.update(config.toDto())
        return config
    }

    private fun AnalyticsPlatformConfig.toDto() = AnalyticsPlatformConfigDto(
        platform = platform,
        isEnabled = isEnabled,
        updatedAt = updatedAt,
    )

    private fun AnalyticsPlatformConfigDto.toDomain() = AnalyticsPlatformConfig(
        platform = platform,
        isEnabled = isEnabled,
        updatedAt = updatedAt,
    )
}
