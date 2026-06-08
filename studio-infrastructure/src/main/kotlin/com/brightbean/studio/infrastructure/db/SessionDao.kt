package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

data class SessionDto(
    val id: UUID,
    val userId: UUID,
    val tokenHash: String,
    val deviceInfo: String?,
    val ipAddress: String?,
    val expiresAt: Instant,
    val createdAt: Instant,
)

@RegisterKotlinMapper(SessionDto::class)
interface SessionDao {
    @SqlQuery("SELECT * FROM accounts_session WHERE id = :id")
    fun findById(id: UUID): SessionDto?

    @SqlQuery("SELECT * FROM accounts_session WHERE token_hash = :tokenHash")
    fun findByTokenHash(tokenHash: String): SessionDto?

    @SqlQuery("SELECT * FROM accounts_session WHERE user_id = :userId AND expires_at > NOW() ORDER BY created_at DESC")
    fun findActiveByUserId(userId: UUID): List<SessionDto>

    @SqlUpdate("INSERT INTO accounts_session (id, user_id, token_hash, device_info, ip_address, expires_at, created_at) VALUES (:dto.id, :dto.userId, :dto.tokenHash, :dto.deviceInfo, :dto.ipAddress, :dto.expiresAt, :dto.createdAt)")
    fun insert(dto: SessionDto)

    @SqlUpdate("DELETE FROM accounts_session WHERE id = :id")
    fun delete(id: UUID)

    @SqlUpdate("DELETE FROM accounts_session WHERE user_id = :userId")
    fun deleteByUserId(userId: UUID)
}
