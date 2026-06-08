package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.OAuthConnection
import com.brightbean.studio.domain.repository.OAuthConnectionRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIOAuthConnectionRepository(jdbi: Jdbi) : OAuthConnectionRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: OAuthConnectionDao by lazy { jdbi.onDemand(OAuthConnectionDao::class.java) }

    override fun findById(id: UUID): OAuthConnection? =
        dao.findById(id)?.toDomain()

    override fun findByUserIdAndProvider(userId: UUID, provider: String): OAuthConnection? =
        dao.findByUserIdAndProvider(userId, provider)?.toDomain()

    override fun findByProviderUser(provider: String, providerUserId: String): OAuthConnection? =
        dao.findByProviderUser(provider, providerUserId)?.toDomain()

    override fun save(connection: OAuthConnection): OAuthConnection {
        dao.insert(connection.toDto())
        return connection
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun OAuthConnection.toDto() = OAuthConnectionDto(
        id = id,
        userId = userId,
        provider = provider,
        providerUserId = providerUserId,
        providerEmail = providerEmail,
        createdAt = createdAt,
    )

    private fun OAuthConnectionDto.toDomain() = OAuthConnection(
        id = id,
        userId = userId,
        provider = provider,
        providerUserId = providerUserId,
        providerEmail = providerEmail,
        createdAt = createdAt,
    )
}
