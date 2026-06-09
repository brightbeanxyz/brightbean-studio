package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.ContentCategory
import com.brightbean.studio.domain.repository.ContentCategoryRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIContentCategoryRepository(jdbi: Jdbi) : ContentCategoryRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: ContentCategoryDao by lazy { jdbi.onDemand(ContentCategoryDao::class.java) }

    override fun findById(id: UUID): ContentCategory? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<ContentCategory> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(category: ContentCategory): ContentCategory {
        dao.insert(category.toDto())
        return category
    }

    override fun update(category: ContentCategory): ContentCategory {
        dao.update(category.toDto())
        return category
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun ContentCategory.toDto() = ContentCategoryDto(
        id = id, workspaceId = workspaceId, name = name, color = color,
        position = position, createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun ContentCategoryDto.toDomain() = ContentCategory(
        id = id, workspaceId = workspaceId, name = name, color = color,
        position = position, createdAt = createdAt, updatedAt = updatedAt,
    )
}
