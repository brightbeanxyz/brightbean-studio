package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Workspace
import java.util.UUID

interface WorkspaceRepository {
    fun findById(id: UUID): Workspace?
    fun findBySlug(slug: String): Workspace?
    fun findByOrganizationId(organizationId: UUID): List<Workspace>
    fun save(workspace: Workspace): Workspace
    fun delete(id: UUID)
}
