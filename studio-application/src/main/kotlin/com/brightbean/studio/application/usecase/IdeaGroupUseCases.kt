package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.IdeaGroup
import com.brightbean.studio.domain.repository.IdeaGroupRepository
import java.time.Instant
import java.util.UUID

class IdeaGroupUseCases(private val repository: IdeaGroupRepository) {

    fun list(workspaceId: UUID): List<IdeaGroup> =
        repository.findByWorkspaceId(workspaceId)

    fun create(workspaceId: UUID, name: String): IdeaGroup {
        val existing = repository.findByWorkspaceId(workspaceId)
        val group = IdeaGroup(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = name,
            position = existing.size,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return repository.save(group)
    }

    fun delete(groupId: UUID) {
        repository.delete(groupId)
    }

    fun reorder(orderedIds: List<UUID>) {
        orderedIds.forEachIndexed { index, id ->
            val group = repository.findById(id) ?: return@forEachIndexed
            repository.update(group.copy(position = index, updatedAt = Instant.now()))
        }
    }
}
