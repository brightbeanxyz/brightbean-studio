package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.MagicLinkToken
import com.brightbean.studio.domain.repository.MagicLinkTokenRepository
import java.time.Instant
import java.util.UUID

data class MagicLinkResult(val userId: UUID, val workspaceId: UUID, val isValid: Boolean)

class ClientPortalUseCases(
    private val magicLinkTokenRepo: MagicLinkTokenRepository,
) {
    fun generateMagicLink(workspaceId: UUID, userId: UUID, createdBy: UUID): MagicLinkToken {
        magicLinkTokenRepo.revokeAllForUserAndWorkspace(userId, workspaceId)
        val token = MagicLinkToken(
            id = UUID.randomUUID(),
            userId = userId,
            workspaceId = workspaceId,
            token = UUID.randomUUID().toString(),
            createdAt = Instant.now(),
            expiresAt = Instant.now().plusSeconds(30 * 24 * 60 * 60L),
            lastUsedAt = null,
            isConsumed = false,
        )
        return magicLinkTokenRepo.save(token)
    }

    fun peekMagicLink(token: String): MagicLinkToken? {
        val link = magicLinkTokenRepo.findByToken(token) ?: return null
        val isValid = !link.isConsumed && Instant.now().isBefore(link.expiresAt)
        return if (isValid) link else null
    }

    fun consumeMagicLink(token: String): MagicLinkResult {
        val link = magicLinkTokenRepo.findByToken(token)
            ?: return MagicLinkResult(UUID.randomUUID(), UUID.randomUUID(), false)

        val isExpired = Instant.now().isAfter(link.expiresAt)
        if (link.isConsumed || isExpired) {
            return MagicLinkResult(link.userId, link.workspaceId, false)
        }

        val consumed = link.copy(isConsumed = true, lastUsedAt = Instant.now())
        magicLinkTokenRepo.update(consumed)
        return MagicLinkResult(link.userId, link.workspaceId, true)
    }

    fun revokeMagicLink(tokenId: UUID, workspaceId: UUID) {
        val token = magicLinkTokenRepo.findByToken(tokenId.toString())
        if (token != null && token.workspaceId == workspaceId) {
            magicLinkTokenRepo.update(token.copy(isConsumed = true, expiresAt = Instant.now()))
        }
    }
}
