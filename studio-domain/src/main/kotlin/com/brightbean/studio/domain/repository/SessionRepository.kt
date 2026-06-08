package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Session
import java.util.UUID

interface SessionRepository {
    fun findById(id: UUID): Session?
    fun findByTokenHash(tokenHash: String): Session?
    fun findActiveByUserId(userId: UUID): List<Session>
    fun save(session: Session): Session
    fun delete(id: UUID)
    fun deleteByUserId(userId: UUID)
}
