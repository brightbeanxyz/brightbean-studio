package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PlatformCredential
import java.util.UUID

interface PlatformCredentialRepository {
    fun findById(id: UUID): PlatformCredential?
    fun findByOrganizationId(organizationId: UUID): List<PlatformCredential>
    fun findByOrgAndPlatform(organizationId: UUID, platform: String): PlatformCredential?
    fun save(credential: PlatformCredential): PlatformCredential
    fun update(credential: PlatformCredential): PlatformCredential
    fun delete(id: UUID)
}
