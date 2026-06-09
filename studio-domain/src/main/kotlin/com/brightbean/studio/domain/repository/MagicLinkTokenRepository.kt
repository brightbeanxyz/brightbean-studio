package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.MagicLinkToken
import java.util.UUID

interface MagicLinkTokenRepository {
    fun findByToken(token: String): MagicLinkToken?
    fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): List<MagicLinkToken>
    fun save(token: MagicLinkToken): MagicLinkToken
    fun update(token: MagicLinkToken): MagicLinkToken
    fun revokeAllForUserAndWorkspace(userId: UUID, workspaceId: UUID)
}
