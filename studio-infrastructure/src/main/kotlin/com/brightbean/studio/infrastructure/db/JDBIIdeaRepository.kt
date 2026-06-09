package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Idea
import com.brightbean.studio.domain.model.IdeaStatus
import com.brightbean.studio.domain.repository.IdeaRepository
import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIIdeaRepository(jdbi: Jdbi) : IdeaRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: IdeaDao by lazy { jdbi.onDemand(IdeaDao::class.java) }

    override fun findById(id: UUID): Idea? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Idea> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByGroupId(groupId: UUID): List<Idea> =
        dao.findByGroupId(groupId).map { it.toDomain() }

    override fun findByAuthorId(authorId: UUID): List<Idea> =
        dao.findByAuthorId(authorId).map { it.toDomain() }

    override fun save(idea: Idea): Idea {
        dao.insert(idea.toDto())
        return idea
    }

    override fun update(idea: Idea): Idea {
        dao.update(idea.toDto())
        return idea
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun Idea.toDto() = IdeaDto(
        id = id, workspaceId = workspaceId, authorId = authorId, title = title,
        description = description, tags = objectMapper.writeValueAsString(tags),
        mediaAssetId = mediaAssetId, status = status.name, groupId = groupId,
        position = position, postId = postId, createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun IdeaDto.toDomain(): Idea {
        val tagList: List<String> = try {
            objectMapper.readValue(tags, object : TypeReference<List<String>>() {})
        } catch (_: Exception) { emptyList() }
        return Idea(
            id = id, workspaceId = workspaceId, authorId = authorId, title = title,
            description = description, tags = tagList, mediaAssetId = mediaAssetId,
            status = try { IdeaStatus.valueOf(status) } catch (_: Exception) { IdeaStatus.UNASSIGNED },
            groupId = groupId, position = position, postId = postId,
            createdAt = createdAt, updatedAt = updatedAt,
        )
    }
}
