package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.InboxItemType
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Sentiment
import com.brightbean.studio.domain.repository.InboxRepository
import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIInboxRepository(jdbi: Jdbi) : InboxRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: InboxItemDao by lazy { jdbi.onDemand(InboxItemDao::class.java) }

    override fun findById(id: UUID): InboxItem? =
        dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<InboxItem> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findBySocialAccountId(socialAccountId: UUID): List<InboxItem> =
        dao.findBySocialAccountId(socialAccountId).map { it.toDomain() }

    override fun save(inboxItem: InboxItem): InboxItem {
        dao.insert(inboxItem.toDto())
        return inboxItem
    }

    override fun update(inboxItem: InboxItem): InboxItem {
        dao.update(inboxItem.toDto())
        return inboxItem
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun InboxItem.toDto() = InboxItemDto(
        id = id,
        workspaceId = workspaceId,
        socialAccountId = socialAccountId,
        platformType = platformType.name,
        platformItemId = platformItemId,
        type = type.name,
        content = content,
        authorName = authorName,
        authorAvatarUrl = authorAvatarUrl,
        mediaUrls = objectMapper.writeValueAsString(mediaUrls),
        sentiment = sentiment?.name,
        isRead = isRead,
        isArchived = isArchived,
        platformCreatedAt = platformCreatedAt,
        receivedAt = receivedAt,
    )

    private fun InboxItemDto.toDomain(): InboxItem {
        val urls: List<String> = try {
            objectMapper.readValue(mediaUrls, object : TypeReference<List<String>>() {})
        } catch (_: Exception) {
            emptyList()
        }
        return InboxItem(
            id = id,
            workspaceId = workspaceId,
            socialAccountId = socialAccountId,
            platformType = PlatformType.valueOf(platformType),
            platformItemId = platformItemId,
            type = InboxItemType.valueOf(type),
            content = content,
            authorName = authorName,
            authorAvatarUrl = authorAvatarUrl,
            mediaUrls = urls,
            sentiment = sentiment?.let { Sentiment.valueOf(it) },
            isRead = isRead,
            isArchived = isArchived,
            platformCreatedAt = platformCreatedAt,
            receivedAt = receivedAt,
        )
    }
}
