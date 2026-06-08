package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.WorkspaceMembership
import com.brightbean.studio.domain.model.WorkspaceRole
import com.brightbean.studio.domain.repository.WorkspaceMembershipRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIWorkspaceMembershipRepository(jdbi: Jdbi) : WorkspaceMembershipRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: WorkspaceMembershipDao by lazy { jdbi.onDemand(WorkspaceMembershipDao::class.java) }

    override fun findById(id: UUID): WorkspaceMembership? =
        dao.findById(id)?.toDomain()

    override fun findByUserId(userId: UUID): List<WorkspaceMembership> =
        dao.findByUserId(userId).map { it.toDomain() }

    override fun findByWorkspaceId(workspaceId: UUID): List<WorkspaceMembership> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): WorkspaceMembership? =
        dao.findByUserAndWorkspace(userId, workspaceId)?.toDomain()

    override fun save(membership: WorkspaceMembership): WorkspaceMembership {
        dao.insert(membership.toDto())
        return membership
    }

    override fun update(membership: WorkspaceMembership): WorkspaceMembership {
        dao.update(membership.toDto())
        return membership
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun WorkspaceMembership.toDto() = WorkspaceMembershipDto(
        id = id,
        userId = userId,
        workspaceId = workspaceId,
        workspaceRole = workspaceRole.name,
        customRoleId = customRoleId,
        addedAt = addedAt,
    )

    private fun WorkspaceMembershipDto.toDomain() = WorkspaceMembership(
        id = id,
        userId = userId,
        workspaceId = workspaceId,
        workspaceRole = WorkspaceRole.valueOf(workspaceRole),
        customRoleId = customRoleId,
        addedAt = addedAt,
    )
}
