package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ContentCategory
import java.util.UUID

interface ContentCategoryRepository {
    fun findById(id: UUID): ContentCategory?
    fun findByWorkspaceId(workspaceId: UUID): List<ContentCategory>
    fun save(category: ContentCategory): ContentCategory
    fun update(category: ContentCategory): ContentCategory
    fun delete(id: UUID)
}
