package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(WorkspaceMembershipDto::class)
interface WorkspaceMembershipDao {
    @SqlQuery("SELECT * FROM workspace_membership WHERE id = :id")
    fun findById(id: UUID): WorkspaceMembershipDto?

    @SqlQuery("SELECT * FROM workspace_membership WHERE user_id = :userId")
    fun findByUserId(userId: UUID): List<WorkspaceMembershipDto>

    @SqlQuery("SELECT * FROM workspace_membership WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<WorkspaceMembershipDto>

    @SqlQuery("SELECT * FROM workspace_membership WHERE user_id = :userId AND workspace_id = :workspaceId")
    fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): WorkspaceMembershipDto?

    @SqlUpdate("""
        INSERT INTO workspace_membership (id, user_id, workspace_id, workspace_role, custom_role_id, added_at)
        VALUES (:dto.id, :dto.userId, :dto.workspaceId, :dto.workspaceRole, :dto.customRoleId, :dto.addedAt)
    """)
    fun insert(dto: WorkspaceMembershipDto)

    @SqlUpdate("""
        UPDATE workspace_membership SET
            workspace_role = :dto.workspaceRole,
            custom_role_id = :dto.customRoleId
        WHERE id = :dto.id
    """)
    fun update(dto: WorkspaceMembershipDto)

    @SqlUpdate("DELETE FROM workspace_membership WHERE id = :id")
    fun delete(id: UUID)
}

data class WorkspaceMembershipDto(
    val id: UUID,
    val userId: UUID,
    val workspaceId: UUID,
    val workspaceRole: String,
    val customRoleId: UUID?,
    val addedAt: java.time.Instant,
)
