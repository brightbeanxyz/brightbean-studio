package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterBeanMapper(CredentialDto::class)
interface CredentialDao {
    @SqlQuery("SELECT * FROM credential WHERE id = :id")
    fun findById(id: UUID): CredentialDto?

    @SqlQuery("SELECT * FROM credential WHERE workspace_id = :workspaceId AND platform_type = :platformType")
    fun findByWorkspaceAndPlatform(workspaceId: UUID, platformType: String): CredentialDto?

    @SqlQuery("SELECT * FROM credential WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<CredentialDto>

    @SqlUpdate("""
        INSERT INTO credential (id, workspace_id, platform_type, encrypted_access_token, encrypted_refresh_token, token_expires_at, metadata, created_at, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.platformType, :dto.encryptedAccessToken, :dto.encryptedRefreshToken, :dto.tokenExpiresAt, :dto.metadata, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: CredentialDto)

    @SqlUpdate("""
        UPDATE credential SET
            encrypted_access_token = :dto.encryptedAccessToken,
            encrypted_refresh_token = :dto.encryptedRefreshToken,
            token_expires_at = :dto.tokenExpiresAt,
            metadata = :dto.metadata,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: CredentialDto)

    @SqlUpdate("DELETE FROM credential WHERE id = :id")
    fun delete(id: UUID)
}

data class CredentialDto(
    val id: UUID,
    val workspaceId: UUID,
    val platformType: String,
    val encryptedAccessToken: String,
    val encryptedRefreshToken: String?,
    val tokenExpiresAt: java.time.Instant?,
    val metadata: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
