package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.IdeaGroup
import com.brightbean.studio.domain.repository.IdeaGroupRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIIdeaGroupRepository(jdbi: Jdbi) : IdeaGroupRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: IdeaGroupDao by lazy { jdbi.onDemand(IdeaGroupDao::class.java) }

    override fun findById(id: UUID): IdeaGroup? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<IdeaGroup> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(group: IdeaGroup): IdeaGroup {
        dao.insert(group.toDto())
        return group
    }

    override fun update(group: IdeaGroup): IdeaGroup {
        dao.update(group.toDto())
        return group
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun IdeaGroup.toDto() = IdeaGroupDto(
        id = id, workspaceId = workspaceId, name = name, position = position,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun IdeaGroupDto.toDomain() = IdeaGroup(
        id = id, workspaceId = workspaceId, name = name, position = position,
        createdAt = createdAt, updatedAt = updatedAt,
    )
}
