package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Workspace
import com.brightbean.studio.domain.model.WorkspaceSettings
import com.brightbean.studio.domain.repository.WorkspaceRepository
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIWorkspaceRepository(jdbi: Jdbi) : WorkspaceRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val workspaceDao: WorkspaceDao by lazy {
        jdbi.onDemand(WorkspaceDao::class.java)
    }

    override fun findById(id: UUID): Workspace? {
        val dto = workspaceDao.findById(id) ?: return null
        return dto.toDomain()
    }

    override fun findBySlug(slug: String): Workspace? {
        val dto = workspaceDao.findBySlug(slug) ?: return null
        return dto.toDomain()
    }

    override fun findByOrganizationId(organizationId: UUID): List<Workspace> =
        workspaceDao.findByOrganizationId(organizationId).map { it.toDomain() }

    override fun save(workspace: Workspace): Workspace {
        val settingsJson = objectMapper.writeValueAsString(workspace.settings)
        val dto = WorkspaceDto(
            id = workspace.id,
            organizationId = workspace.organizationId,
            name = workspace.name,
            slug = workspace.slug,
            ownerId = workspace.ownerId,
            settings = settingsJson,
            isArchived = workspace.isArchived,
            createdAt = workspace.createdAt,
            updatedAt = workspace.updatedAt,
        )
        workspaceDao.insert(dto)
        return workspace
    }

    override fun delete(id: UUID) {
        workspaceDao.delete(id)
    }

    private fun WorkspaceDto.toDomain(): Workspace {
        val settings = objectMapper.readValue(settings, WorkspaceSettings::class.java)
        return Workspace(
            id = id,
            organizationId = organizationId,
            name = name,
            slug = slug,
            ownerId = ownerId,
            settings = settings,
            isArchived = isArchived,
            createdAt = createdAt,
            updatedAt = updatedAt,
        )
    }
}
