package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PlatformVisibility

interface PlatformVisibilityRepository {
    fun findByPlatform(platform: String): PlatformVisibility?
    fun findAll(): List<PlatformVisibility>
    fun save(visibility: PlatformVisibility): PlatformVisibility
    fun update(visibility: PlatformVisibility): PlatformVisibility
}
