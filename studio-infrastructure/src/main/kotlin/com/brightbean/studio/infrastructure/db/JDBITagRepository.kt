package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Tag
import com.brightbean.studio.domain.repository.TagRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBITagRepository(jdbi: Jdbi) : TagRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: TagDao by lazy { jdbi.onDemand(TagDao::class.java) }

    override fun findById(id: UUID): Tag? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Tag> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByName(workspaceId: UUID, name: String): Tag? =
        dao.findByName(workspaceId, name)?.toDomain()

    override fun save(tag: Tag): Tag {
        dao.insert(tag.toDto())
        return tag
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun Tag.toDto() = TagDto(
        id = id, workspaceId = workspaceId, name = name, createdAt = createdAt,
    )

    private fun TagDto.toDomain() = Tag(
        id = id, workspaceId = workspaceId, name = name, createdAt = createdAt,
    )
}
