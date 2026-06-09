package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate

@RegisterKotlinMapper(PlatformVisibilityDto::class)
interface PlatformVisibilityDao {
    @SqlQuery("SELECT * FROM platform_visibility WHERE platform = :platform")
    fun findByPlatform(platform: String): PlatformVisibilityDto?

    @SqlQuery("SELECT * FROM platform_visibility")
    fun findAll(): List<PlatformVisibilityDto>

    @SqlUpdate("""
        INSERT INTO platform_visibility (platform, is_visible, updated_at)
        VALUES (:dto.platform, :dto.isVisible, :dto.updatedAt)
    """)
    fun insert(dto: PlatformVisibilityDto)

    @SqlUpdate("""
        UPDATE platform_visibility SET
            is_visible = :dto.isVisible,
            updated_at = :dto.updatedAt
        WHERE platform = :dto.platform
    """)
    fun update(dto: PlatformVisibilityDto)
}

data class PlatformVisibilityDto(
    val platform: String,
    val isVisible: Boolean,
    val updatedAt: java.time.Instant,
)
