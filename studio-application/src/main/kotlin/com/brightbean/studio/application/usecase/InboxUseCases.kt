package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.InboxMessage
import com.brightbean.studio.domain.model.InboxMessageStatus
import com.brightbean.studio.domain.model.InboxMessageType
import com.brightbean.studio.domain.model.InboxSLAConfig
import com.brightbean.studio.domain.model.SavedReply
import com.brightbean.studio.domain.repository.InboxMessageRepository
import com.brightbean.studio.domain.repository.InboxReplyRepository
import com.brightbean.studio.domain.repository.InboxSLAConfigRepository
import com.brightbean.studio.domain.repository.InternalNoteRepository
import com.brightbean.studio.domain.repository.SavedReplyRepository
import java.time.Instant
import java.util.UUID

class InboxUseCases(
    private val inboxMessageRepository: InboxMessageRepository,
    private val inboxReplyRepository: InboxReplyRepository,
    private val internalNoteRepository: InternalNoteRepository,
    private val savedReplyRepository: SavedReplyRepository,
    private val inboxSLAConfigRepository: InboxSLAConfigRepository,
) {
    fun listMessages(workspaceId: UUID, status: InboxMessageStatus? = null): List<InboxMessage> =
        if (status != null) inboxMessageRepository.findByStatus(workspaceId, status)
        else inboxMessageRepository.findByWorkspaceId(workspaceId)

    fun getMessage(messageId: UUID): InboxMessage? = inboxMessageRepository.findById(messageId)

    fun sendReply(messageId: UUID, authorId: UUID?, body: String, platformReplyId: String) =
        inboxReplyRepository.save(
            com.brightbean.studio.domain.model.InboxReply(
                id = UUID.randomUUID(),
                inboxMessageId = messageId,
                authorId = authorId,
                body = body,
                platformReplyId = platformReplyId,
                sentAt = Instant.now(),
            )
        )

    fun addNote(messageId: UUID, authorId: UUID?, body: String) =
        internalNoteRepository.save(
            com.brightbean.studio.domain.model.InternalNote(
                id = UUID.randomUUID(),
                inboxMessageId = messageId,
                authorId = authorId,
                body = body,
                createdAt = Instant.now(),
            )
        )

    fun assignMessage(messageId: UUID, userId: UUID?): InboxMessage {
        val message = inboxMessageRepository.findById(messageId) ?: throw IllegalArgumentException("Message not found: $messageId")
        val updated = message.copy(assignedTo = userId, status = InboxMessageStatus.OPEN)
        return inboxMessageRepository.update(updated)
    }

    fun changeStatus(messageId: UUID, status: InboxMessageStatus): InboxMessage {
        val message = inboxMessageRepository.findById(messageId) ?: throw IllegalArgumentException("Message not found: $messageId")
        return inboxMessageRepository.update(message.copy(status = status))
    }

    fun changeSentiment(messageId: UUID, sentiment: String, source: String): InboxMessage {
        val message = inboxMessageRepository.findById(messageId) ?: throw IllegalArgumentException("Message not found: $messageId")
        return inboxMessageRepository.update(message.copy(sentiment = sentiment, sentimentSource = source))
    }

    fun bulkAction(messageIds: List<UUID>, action: String) {
        for (id in messageIds) {
            when (action) {
                "archive" -> { val m = inboxMessageRepository.findById(id) ?: continue; inboxMessageRepository.update(m.copy(status = InboxMessageStatus.ARCHIVED)) }
                "resolve" -> { val m = inboxMessageRepository.findById(id) ?: continue; inboxMessageRepository.update(m.copy(status = InboxMessageStatus.RESOLVED)) }
                "delete" -> inboxMessageRepository.delete(id)
            }
        }
    }

    fun listSavedReplies(workspaceId: UUID): List<SavedReply> = savedReplyRepository.findByWorkspaceId(workspaceId)

    fun createSavedReply(workspaceId: UUID, title: String, body: String, createdBy: UUID?): SavedReply =
        savedReplyRepository.save(SavedReply(id = UUID.randomUUID(), workspaceId = workspaceId, title = title, body = body, createdBy = createdBy, createdAt = Instant.now(), updatedAt = Instant.now()))

    fun deleteSavedReply(id: UUID) = savedReplyRepository.delete(id)

    fun getSLAConfig(workspaceId: UUID): InboxSLAConfig? = inboxSLAConfigRepository.findByWorkspaceId(workspaceId)

    fun updateSLAConfig(config: InboxSLAConfig): InboxSLAConfig =
        if (inboxSLAConfigRepository.findByWorkspaceId(config.workspaceId) == null) inboxSLAConfigRepository.save(config)
        else inboxSLAConfigRepository.update(config)
}
