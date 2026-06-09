package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.InboxMessage
import com.brightbean.studio.domain.model.InboxMessageStatus
import com.brightbean.studio.domain.model.InboxMessageType
import com.brightbean.studio.domain.model.InboxReply
import com.brightbean.studio.domain.model.InboxSLAConfig
import com.brightbean.studio.domain.model.InternalNote
import com.brightbean.studio.domain.model.SavedReply
import com.brightbean.studio.domain.repository.InboxMessageRepository
import com.brightbean.studio.domain.repository.InboxReplyRepository
import com.brightbean.studio.domain.repository.InboxSLAConfigRepository
import com.brightbean.studio.domain.repository.InternalNoteRepository
import com.brightbean.studio.domain.repository.SavedReplyRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIInboxMessageRepository(jdbi: Jdbi) : InboxMessageRepository {
    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }
    private val dao: InboxMessageDao by lazy { jdbi.onDemand(InboxMessageDao::class.java) }

    override fun findById(id: UUID): InboxMessage? = dao.findById(id)?.toDomain()
    override fun findByWorkspaceId(workspaceId: UUID): List<InboxMessage> = dao.findByWorkspaceId(workspaceId).map { it.toDomain() }
    override fun findByStatus(workspaceId: UUID, status: InboxMessageStatus): List<InboxMessage> = dao.findByStatus(workspaceId, status.name).map { it.toDomain() }
    override fun findByAssignedTo(workspaceId: UUID, userId: UUID): List<InboxMessage> = dao.findByAssignedTo(workspaceId, userId).map { it.toDomain() }
    override fun findByPlatformMessageId(socialAccountId: UUID, platformMessageId: String): InboxMessage? = dao.findByPlatformMessageId(socialAccountId, platformMessageId)?.toDomain()
    override fun save(message: InboxMessage): InboxMessage { dao.insert(message.toDto()); return message }
    override fun update(message: InboxMessage): InboxMessage { dao.update(message.toDto()); return message }
    override fun delete(id: UUID) = dao.delete(id)

    private fun InboxMessage.toDto() = InboxMessageDto(id, workspaceId, socialAccountId, platformMessageId, messageType.name, senderName, senderHandle, senderAvatarUrl, body, sentiment, sentimentSource, status.name, assignedTo, parentMessageId, relatedPostId, extra, receivedAt, createdAt)
    private fun InboxMessageDto.toDomain() = InboxMessage(id, workspaceId, socialAccountId, platformMessageId, InboxMessageType.valueOf(messageType), senderName, senderHandle, senderAvatarUrl, body, sentiment, sentimentSource, InboxMessageStatus.valueOf(status), assignedTo, parentMessageId, relatedPostId, extra, receivedAt, createdAt)
}

class JDBIInboxReplyRepository(jdbi: Jdbi) : InboxReplyRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: InboxReplyDao by lazy { jdbi.onDemand(InboxReplyDao::class.java) }

    override fun findByMessageId(inboxMessageId: UUID): List<InboxReply> = dao.findByMessageId(inboxMessageId).map { it.toDomain() }
    override fun save(reply: InboxReply): InboxReply { dao.insert(reply.toDto()); return reply }
    override fun delete(id: UUID) = dao.delete(id)

    private fun InboxReply.toDto() = InboxReplyDto(id, inboxMessageId, authorId, body, platformReplyId, sentAt)
    private fun InboxReplyDto.toDomain() = InboxReply(id, inboxMessageId, authorId, body, platformReplyId, sentAt)
}

class JDBIInternalNoteRepository(jdbi: Jdbi) : InternalNoteRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: InternalNoteDao by lazy { jdbi.onDemand(InternalNoteDao::class.java) }

    override fun findByMessageId(inboxMessageId: UUID): List<InternalNote> = dao.findByMessageId(inboxMessageId).map { it.toDomain() }
    override fun save(note: InternalNote): InternalNote { dao.insert(note.toDto()); return note }
    override fun delete(id: UUID) = dao.delete(id)

    private fun InternalNote.toDto() = InternalNoteDto(id, inboxMessageId, authorId, body, createdAt)
    private fun InternalNoteDto.toDomain() = InternalNote(id, inboxMessageId, authorId, body, createdAt)
}

class JDBISavedReplyRepository(jdbi: Jdbi) : SavedReplyRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: SavedReplyDao by lazy { jdbi.onDemand(SavedReplyDao::class.java) }

    override fun findByWorkspaceId(workspaceId: UUID): List<SavedReply> = dao.findByWorkspaceId(workspaceId).map { it.toDomain() }
    override fun save(reply: SavedReply): SavedReply { dao.insert(reply.toDto()); return reply }
    override fun update(reply: SavedReply): SavedReply { dao.update(reply.toDto()); return reply }
    override fun delete(id: UUID) = dao.delete(id)

    private fun SavedReply.toDto() = SavedReplyDto(id, workspaceId, title, body, createdBy, createdAt, updatedAt)
    private fun SavedReplyDto.toDomain() = SavedReply(id, workspaceId, title, body, createdBy, createdAt, updatedAt)
}

class JDBIInboxSLAConfigRepository(jdbi: Jdbi) : InboxSLAConfigRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: InboxSLAConfigDao by lazy { jdbi.onDemand(InboxSLAConfigDao::class.java) }

    override fun findByWorkspaceId(workspaceId: UUID): InboxSLAConfig? = dao.findByWorkspaceId(workspaceId)?.toDomain()
    override fun save(config: InboxSLAConfig): InboxSLAConfig { dao.insert(config.toDto()); return config }
    override fun update(config: InboxSLAConfig): InboxSLAConfig { dao.update(config.toDto()); return config }

    private fun InboxSLAConfig.toDto() = InboxSLAConfigDto(id, workspaceId, targetResponseMinutes, isActive, autoResolveOnReply)
    private fun InboxSLAConfigDto.toDomain() = InboxSLAConfig(id, workspaceId, targetResponseMinutes, isActive, autoResolveOnReply)
}
