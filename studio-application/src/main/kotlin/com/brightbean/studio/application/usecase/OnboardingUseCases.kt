package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ConnectionLink
import com.brightbean.studio.domain.model.ConnectionLinkUsage
import com.brightbean.studio.domain.model.OnboardingChecklist
import com.brightbean.studio.domain.repository.ConnectionLinkRepository
import com.brightbean.studio.domain.repository.ConnectionLinkUsageRepository
import com.brightbean.studio.domain.repository.OnboardingChecklistRepository
import java.time.Instant
import java.util.UUID

class OnboardingUseCases(
    private val connectionLinkRepo: ConnectionLinkRepository,
    private val connectionLinkUsageRepo: ConnectionLinkUsageRepository,
    private val checklistRepo: OnboardingChecklistRepository,
) {
    fun createConnectionLink(workspaceId: UUID, createdBy: UUID?, expiresAt: Instant): ConnectionLink {
        val link = ConnectionLink(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            token = UUID.randomUUID().toString(),
            createdBy = createdBy,
            expiresAt = expiresAt,
            revokedAt = null,
            createdAt = Instant.now(),
        )
        return connectionLinkRepo.save(link)
    }

    fun revokeConnectionLink(linkId: UUID) {
        val link = connectionLinkRepo.findById(linkId)
            ?: throw IllegalArgumentException("Connection link not found")
        connectionLinkRepo.update(link.copy(revokedAt = Instant.now()))
    }

    fun validateConnectionLink(token: String): ConnectionLink? {
        val link = connectionLinkRepo.findByToken(token) ?: return null
        return if (link.isActive) link else null
    }

    fun recordConnectionUsage(linkId: UUID, socialAccountId: UUID): ConnectionLinkUsage {
        val usage = ConnectionLinkUsage(
            id = UUID.randomUUID(),
            connectionLinkId = linkId,
            socialAccountId = socialAccountId,
            connectedAt = Instant.now(),
        )
        return connectionLinkUsageRepo.save(usage)
    }

    fun getChecklist(userId: UUID, workspaceId: UUID): OnboardingChecklist {
        return checklistRepo.findByUserAndWorkspace(userId, workspaceId)
            ?: checklistRepo.save(OnboardingChecklist(
                id = UUID.randomUUID(),
                userId = userId,
                workspaceId = workspaceId,
                isDismissed = false,
                dismissedAt = null,
            ))
    }

    fun dismissChecklist(userId: UUID, workspaceId: UUID): OnboardingChecklist {
        val checklist = getChecklist(userId, workspaceId)
        return checklistRepo.update(checklist.copy(isDismissed = true, dismissedAt = Instant.now()))
    }
}
