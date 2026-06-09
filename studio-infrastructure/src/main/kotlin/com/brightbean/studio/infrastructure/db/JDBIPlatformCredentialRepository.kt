package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PlatformCredential
import com.brightbean.studio.domain.model.TestResult
import com.brightbean.studio.domain.repository.PlatformCredentialRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPlatformCredentialRepository(jdbi: Jdbi) : PlatformCredentialRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PlatformCredentialDao by lazy { jdbi.onDemand(PlatformCredentialDao::class.java) }

    override fun findById(id: UUID): PlatformCredential? =
        dao.findById(id)?.toDomain()

    override fun findByOrganizationId(organizationId: UUID): List<PlatformCredential> =
        dao.findByOrganizationId(organizationId).map { it.toDomain() }

    override fun findByOrgAndPlatform(organizationId: UUID, platform: String): PlatformCredential? =
        dao.findByOrgAndPlatform(organizationId, platform)?.toDomain()

    override fun save(credential: PlatformCredential): PlatformCredential {
        dao.insert(credential.toDto())
        return credential
    }

    override fun update(credential: PlatformCredential): PlatformCredential {
        dao.update(credential.toDto())
        return credential
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun PlatformCredential.toDto() = PlatformCredentialDto(
        id = id,
        organizationId = organizationId,
        platform = platform,
        credentials = credentials,
        isConfigured = isConfigured,
        testedAt = testedAt,
        testResult = testResult.name,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun PlatformCredentialDto.toDomain() = PlatformCredential(
        id = id,
        organizationId = organizationId,
        platform = platform,
        credentials = credentials,
        isConfigured = isConfigured,
        testedAt = testedAt,
        testResult = TestResult.valueOf(testResult),
        createdAt = createdAt,
        updatedAt = updatedAt,
    )
}
