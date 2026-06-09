package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(PlatformCredentialDto::class)
interface PlatformCredentialDao {
    @SqlQuery("SELECT * FROM platform_credential WHERE id = :id")
    fun findById(id: UUID): PlatformCredentialDto?

    @SqlQuery("SELECT * FROM platform_credential WHERE organization_id = :organizationId")
    fun findByOrganizationId(organizationId: UUID): List<PlatformCredentialDto>

    @SqlQuery("SELECT * FROM platform_credential WHERE organization_id = :organizationId AND platform = :platform")
    fun findByOrgAndPlatform(organizationId: UUID, platform: String): PlatformCredentialDto?

    @SqlUpdate("""
        INSERT INTO platform_credential (id, organization_id, platform, credentials, is_configured, tested_at, test_result, created_at, updated_at)
        VALUES (:dto.id, :dto.organizationId, :dto.platform, :dto.credentials, :dto.isConfigured, :dto.testedAt, :dto.testResult, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: PlatformCredentialDto)

    @SqlUpdate("""
        UPDATE platform_credential SET
            credentials = :dto.credentials,
            is_configured = :dto.isConfigured,
            tested_at = :dto.testedAt,
            test_result = :dto.testResult,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PlatformCredentialDto)

    @SqlUpdate("DELETE FROM platform_credential WHERE id = :id")
    fun delete(id: UUID)
}

data class PlatformCredentialDto(
    val id: UUID,
    val organizationId: UUID,
    val platform: String,
    val credentials: String,
    val isConfigured: Boolean,
    val testedAt: java.time.Instant?,
    val testResult: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
