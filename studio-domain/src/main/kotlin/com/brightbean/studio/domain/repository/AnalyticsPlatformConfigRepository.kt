package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.AnalyticsPlatformConfig

interface AnalyticsPlatformConfigRepository {
    fun findByPlatform(platform: String): AnalyticsPlatformConfig?
    fun findAll(): List<AnalyticsPlatformConfig>
    fun save(config: AnalyticsPlatformConfig): AnalyticsPlatformConfig
    fun update(config: AnalyticsPlatformConfig): AnalyticsPlatformConfig
}
