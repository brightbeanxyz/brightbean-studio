package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ContentCategory
import com.brightbean.studio.domain.repository.ContentCategoryRepository
import java.time.Instant
import java.util.UUID

class ContentCategoryUseCases(private val repository: ContentCategoryRepository) {

    fun list(workspaceId: UUID): List<ContentCategory> =
        repository.findByWorkspaceId(workspaceId)

    fun create(workspaceId: UUID, name: String, color: String): ContentCategory {
        val existing = repository.findByWorkspaceId(workspaceId)
        val nextPosition = existing.size
        val category = ContentCategory(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = name,
            color = color,
            position = nextPosition,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return repository.save(category)
    }

    fun update(id: UUID, name: String?, color: String?): ContentCategory {
        val category = repository.findById(id)
            ?: throw IllegalArgumentException("Category not found: $id")
        val updated = category.copy(
            name = name ?: category.name,
            color = color ?: category.color,
            updatedAt = Instant.now(),
        )
        return repository.update(updated)
    }

    fun delete(id: UUID) {
        repository.delete(id)
    }
}
