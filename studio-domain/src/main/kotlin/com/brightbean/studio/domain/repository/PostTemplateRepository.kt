package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PostTemplate
import java.util.UUID

interface PostTemplateRepository {
    fun findById(id: UUID): PostTemplate?
    fun findByWorkspaceId(workspaceId: UUID): List<PostTemplate>
    fun save(template: PostTemplate): PostTemplate
    fun update(template: PostTemplate): PostTemplate
    fun delete(id: UUID)
}
