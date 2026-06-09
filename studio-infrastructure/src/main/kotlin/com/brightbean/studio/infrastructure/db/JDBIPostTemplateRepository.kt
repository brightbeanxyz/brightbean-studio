package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PostTemplate
import com.brightbean.studio.domain.repository.PostTemplateRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPostTemplateRepository(jdbi: Jdbi) : PostTemplateRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PostTemplateDao by lazy { jdbi.onDemand(PostTemplateDao::class.java) }

    override fun findById(id: UUID): PostTemplate? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<PostTemplate> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(template: PostTemplate): PostTemplate {
        dao.insert(template.toDto())
        return template
    }

    override fun update(template: PostTemplate): PostTemplate {
        dao.update(template.toDto())
        return template
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun PostTemplate.toDto() = PostTemplateDto(
        id = id, workspaceId = workspaceId, name = name, description = description,
        templateData = templateData, createdBy = createdBy,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun PostTemplateDto.toDomain() = PostTemplate(
        id = id, workspaceId = workspaceId, name = name, description = description,
        templateData = templateData, createdBy = createdBy,
        createdAt = createdAt, updatedAt = updatedAt,
    )
}
