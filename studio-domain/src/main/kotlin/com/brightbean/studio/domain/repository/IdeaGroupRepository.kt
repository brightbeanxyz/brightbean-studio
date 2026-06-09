package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.IdeaGroup
import java.util.UUID

interface IdeaGroupRepository {
    fun findById(id: UUID): IdeaGroup?
    fun findByWorkspaceId(workspaceId: UUID): List<IdeaGroup>
    fun save(group: IdeaGroup): IdeaGroup
    fun update(group: IdeaGroup): IdeaGroup
    fun delete(id: UUID)
}
