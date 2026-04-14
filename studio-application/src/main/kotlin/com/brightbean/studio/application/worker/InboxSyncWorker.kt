package com.brightbean.studio.application.worker

import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.InboxRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import java.time.Instant
import java.util.UUID

class InboxSyncWorker(
    private val socialAccountRepository: SocialAccountRepository,
    private val inboxRepository: InboxRepository,
    private val providerRegistry: ProviderRegistry,
) {
    fun syncAllAccounts(workspaceId: UUID) {
        val accounts = socialAccountRepository.findActiveByWorkspace(workspaceId)
        for (account in accounts) {
            syncAccount(account)
        }
    }

    fun syncAccount(account: SocialAccount) {
        val provider = providerRegistry.get(account.platformType) ?: return

        val inboxItems = provider.getInboxItems(account)
        for (item in inboxItems) {
            inboxRepository.save(item)
        }

        val updatedAccount = account.copy(lastSyncAt = Instant.now())
        socialAccountRepository.update(updatedAccount)
    }
}