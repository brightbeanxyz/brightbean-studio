package com.brightbean.studio.application.worker

import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.InboxMessage
import com.brightbean.studio.domain.model.InboxMessageStatus
import com.brightbean.studio.domain.model.InboxMessageType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.InboxMessageRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import java.time.Instant
import java.util.UUID

class InboxSyncWorker(
    private val socialAccountRepository: SocialAccountRepository,
    private val inboxMessageRepository: InboxMessageRepository,
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
            val existing = inboxMessageRepository.findByPlatformMessageId(account.id, item.platformItemId)
            if (existing == null) {
                val message = mapToMessage(item)
                inboxMessageRepository.save(message)
            }
        }

        val updatedAccount = account.copy(lastSyncAt = Instant.now())
        socialAccountRepository.update(updatedAccount)
    }

    private fun mapToMessage(item: InboxItem): InboxMessage = InboxMessage(
        id = item.id,
        workspaceId = item.workspaceId,
        socialAccountId = item.socialAccountId,
        platformMessageId = item.platformItemId,
        messageType = mapType(item.type),
        senderName = item.authorName,
        senderHandle = "",
        senderAvatarUrl = item.authorAvatarUrl ?: "",
        body = item.content,
        sentiment = item.sentiment?.name ?: "NEUTRAL",
        sentimentSource = "auto",
        status = if (item.isRead) InboxMessageStatus.OPEN else InboxMessageStatus.UNREAD,
        assignedTo = null,
        parentMessageId = null,
        relatedPostId = null,
        extra = null,
        receivedAt = item.receivedAt,
        createdAt = item.platformCreatedAt,
    )

    private fun mapType(type: com.brightbean.studio.domain.model.InboxItemType): InboxMessageType = when (type) {
        com.brightbean.studio.domain.model.InboxItemType.COMMENT -> InboxMessageType.COMMENT
        com.brightbean.studio.domain.model.InboxItemType.MENTION -> InboxMessageType.MENTION
        com.brightbean.studio.domain.model.InboxItemType.MESSAGE -> InboxMessageType.DM
        com.brightbean.studio.domain.model.InboxItemType.SHARE -> InboxMessageType.MENTION
    }
}
