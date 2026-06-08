package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.repository.SessionRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBISessionRepository(jdbi: Jdbi) : SessionRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: SessionDao by lazy { jdbi.onDemand(SessionDao::class.java) }

    override fun findById(id: UUID): Session? =
        dao.findById(id)?.toDomain()

    override fun findByTokenHash(tokenHash: String): Session? =
        dao.findByTokenHash(tokenHash)?.toDomain()

    override fun findActiveByUserId(userId: UUID): List<Session> =
        dao.findActiveByUserId(userId).map { it.toDomain() }

    override fun save(session: Session): Session {
        dao.insert(session.toDto())
        return session
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    override fun deleteByUserId(userId: UUID) {
        dao.deleteByUserId(userId)
    }

    private fun Session.toDto() = SessionDto(
        id = id,
        userId = userId,
        tokenHash = tokenHash,
        deviceInfo = deviceInfo,
        ipAddress = ipAddress,
        expiresAt = expiresAt,
        createdAt = createdAt,
    )

    private fun SessionDto.toDomain() = Session(
        id = id,
        userId = userId,
        tokenHash = tokenHash,
        deviceInfo = deviceInfo,
        ipAddress = ipAddress,
        expiresAt = expiresAt,
        createdAt = createdAt,
    )
}
