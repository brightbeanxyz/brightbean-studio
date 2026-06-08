package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.WorkspaceMembership
import java.util.UUID

interface WorkspaceMembershipRepository {
    fun findById(id: UUID): WorkspaceMembership?
    fun findByUserId(userId: UUID): List<WorkspaceMembership>
    fun findByWorkspaceId(workspaceId: UUID): List<WorkspaceMembership>
    fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): WorkspaceMembership?
    fun save(membership: WorkspaceMembership): WorkspaceMembership
    fun update(membership: WorkspaceMembership): WorkspaceMembership
    fun delete(id: UUID)
}
