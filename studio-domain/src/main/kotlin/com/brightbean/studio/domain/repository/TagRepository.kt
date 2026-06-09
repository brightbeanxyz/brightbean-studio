package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Tag
import java.util.UUID

interface TagRepository {
    fun findById(id: UUID): Tag?
    fun findByWorkspaceId(workspaceId: UUID): List<Tag>
    fun findByName(workspaceId: UUID, name: String): Tag?
    fun save(tag: Tag): Tag
    fun delete(id: UUID)
}
