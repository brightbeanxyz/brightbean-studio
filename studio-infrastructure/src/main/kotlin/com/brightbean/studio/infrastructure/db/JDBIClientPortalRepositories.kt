package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.MagicLinkToken
import com.brightbean.studio.domain.repository.MagicLinkTokenRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIMagicLinkTokenRepository(jdbi: Jdbi) : MagicLinkTokenRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: MagicLinkTokenDao by lazy { jdbi.onDemand(MagicLinkTokenDao::class.java) }

    override fun findByToken(token: String): MagicLinkToken? = dao.findByToken(token)?.toDomain()
    override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): List<MagicLinkToken> = dao.findByUserAndWorkspace(userId, workspaceId).map { it.toDomain() }
    override fun save(token: MagicLinkToken): MagicLinkToken { dao.insert(token.toDto()); return token }
    override fun update(token: MagicLinkToken): MagicLinkToken { dao.update(token.toDto()); return token }
    override fun revokeAllForUserAndWorkspace(userId: UUID, workspaceId: UUID) = dao.revokeAllForUserAndWorkspace(userId, workspaceId)

    private fun MagicLinkToken.toDto() = MagicLinkTokenDto(id, userId, workspaceId, token, createdAt, expiresAt, lastUsedAt, isConsumed)
    private fun MagicLinkTokenDto.toDomain() = MagicLinkToken(id, userId, workspaceId, token, createdAt, expiresAt, lastUsedAt, isConsumed)
}
