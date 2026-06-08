package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

data class OAuthConnectionDto(
    val id: UUID,
    val userId: UUID,
    val provider: String,
    val providerUserId: String,
    val providerEmail: String?,
    val createdAt: Instant,
)

@RegisterKotlinMapper(OAuthConnectionDto::class)
interface OAuthConnectionDao {
    @SqlQuery("SELECT * FROM accounts_oauth_connection WHERE id = :id")
    fun findById(id: UUID): OAuthConnectionDto?

    @SqlQuery("SELECT * FROM accounts_oauth_connection WHERE user_id = :userId AND provider = :provider")
    fun findByUserIdAndProvider(userId: UUID, provider: String): OAuthConnectionDto?

    @SqlQuery("SELECT * FROM accounts_oauth_connection WHERE provider = :provider AND provider_user_id = :providerUserId")
    fun findByProviderUser(provider: String, providerUserId: String): OAuthConnectionDto?

    @SqlUpdate("INSERT INTO accounts_oauth_connection (id, user_id, provider, provider_user_id, provider_email, created_at) VALUES (:dto.id, :dto.userId, :dto.provider, :dto.providerUserId, :dto.providerEmail, :dto.createdAt)")
    fun insert(dto: OAuthConnectionDto)

    @SqlUpdate("DELETE FROM accounts_oauth_connection WHERE id = :id")
    fun delete(id: UUID)
}
