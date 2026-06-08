package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

data class UserDto(
    val id: UUID,
    val email: String,
    val name: String,
    val passwordHash: String,
    val avatar: String?,
    val totpSecret: String?,
    val totpRecoveryCodes: String?,
    val totpEnabled: Boolean,
    val lastWorkspaceId: UUID?,
    val tosAcceptedAt: Instant?,
    val isActive: Boolean,
    val createdAt: Instant,
    val updatedAt: Instant,
)

@RegisterKotlinMapper(UserDto::class)
interface UserDao {
    @SqlQuery("SELECT * FROM accounts_user WHERE id = :id")
    fun findById(id: UUID): UserDto?

    @SqlQuery("SELECT * FROM accounts_user WHERE email = :email")
    fun findByEmail(email: String): UserDto?

    @SqlUpdate("""
        INSERT INTO accounts_user (id, email, name, password_hash, avatar, totp_secret, totp_recovery_codes, totp_enabled, last_workspace_id, tos_accepted_at, is_active, created_at, updated_at)
        VALUES (:dto.id, :dto.email, :dto.name, :dto.passwordHash, :dto.avatar, :dto.totpSecret, :dto.totpRecoveryCodes, :dto.totpEnabled, :dto.lastWorkspaceId, :dto.tosAcceptedAt, :dto.isActive, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: UserDto)

    @SqlUpdate("""
        UPDATE accounts_user SET email = :dto.email, name = :dto.name, password_hash = :dto.passwordHash, avatar = :dto.avatar, totp_secret = :dto.totpSecret, totp_recovery_codes = :dto.totpRecoveryCodes, totp_enabled = :dto.totpEnabled, last_workspace_id = :dto.lastWorkspaceId, tos_accepted_at = :dto.tosAcceptedAt, is_active = :dto.isActive, updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: UserDto)

    @SqlUpdate("DELETE FROM accounts_user WHERE id = :id")
    fun delete(id: UUID)
}
