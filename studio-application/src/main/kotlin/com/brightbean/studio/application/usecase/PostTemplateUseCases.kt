package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PostTemplate
import com.brightbean.studio.domain.repository.PostTemplateRepository
import java.time.Instant
import java.util.UUID

class PostTemplateUseCases(private val repository: PostTemplateRepository) {

    fun list(workspaceId: UUID): List<PostTemplate> =
        repository.findByWorkspaceId(workspaceId)

    fun saveAsTemplate(
        workspaceId: UUID,
        name: String,
        description: String,
        templateData: String,
        createdBy: UUID?,
    ): PostTemplate {
        val template = PostTemplate(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = name,
            description = description,
            templateData = templateData,
            createdBy = createdBy,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return repository.save(template)
    }

    fun delete(id: UUID) {
        repository.delete(id)
    }
}
