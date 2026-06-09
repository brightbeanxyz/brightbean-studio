package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PlatformVisibility
import com.brightbean.studio.domain.repository.PlatformVisibilityRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin

class JDBIPlatformVisibilityRepository(jdbi: Jdbi) : PlatformVisibilityRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PlatformVisibilityDao by lazy { jdbi.onDemand(PlatformVisibilityDao::class.java) }

    override fun findByPlatform(platform: String): PlatformVisibility? =
        dao.findByPlatform(platform)?.toDomain()

    override fun findAll(): List<PlatformVisibility> =
        dao.findAll().map { it.toDomain() }

    override fun save(visibility: PlatformVisibility): PlatformVisibility {
        dao.insert(visibility.toDto())
        return visibility
    }

    override fun update(visibility: PlatformVisibility): PlatformVisibility {
        dao.update(visibility.toDto())
        return visibility
    }

    private fun PlatformVisibility.toDto() = PlatformVisibilityDto(
        platform = platform,
        isVisible = isVisible,
        updatedAt = updatedAt,
    )

    private fun PlatformVisibilityDto.toDomain() = PlatformVisibility(
        platform = platform,
        isVisible = isVisible,
        updatedAt = updatedAt,
    )
}
