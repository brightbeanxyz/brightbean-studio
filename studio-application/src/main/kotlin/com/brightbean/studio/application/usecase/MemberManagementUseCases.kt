package com.brightbean.studio.application.usecase

import com.brightbean.studio.application.auth.ORG_ROLE_LEVEL
import com.brightbean.studio.application.auth.WORKSPACE_ROLE_LEVEL
import com.brightbean.studio.domain.model.OrgMembership
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.WorkspaceMembership
import com.brightbean.studio.domain.repository.OrgMembershipRepository
import com.brightbean.studio.domain.repository.WorkspaceMembershipRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import java.time.Instant
import java.util.UUID

class UpdateMemberOrgRoleUseCase(
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(orgId: UUID, membershipId: UUID, newRole: OrgRole, callerId: UUID): Result<OrgMembership> {
        val membership = orgMembershipRepository.findById(membershipId)
            ?: return Result.failure(IllegalArgumentException("Membership not found"))
        if (membership.organizationId != orgId) {
            return Result.failure(IllegalArgumentException("Membership does not belong to this organization"))
        }
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, orgId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        val callerLevel = ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0
        if (callerLevel < ORG_ROLE_LEVEL[OrgRole.ADMIN]!!) {
            return Result.failure(IllegalArgumentException("Only org admins can update member roles"))
        }
        if (newRole == OrgRole.OWNER) {
            return Result.failure(IllegalArgumentException("Cannot promote to owner. Use ownership transfer instead."))
        }
        val existingLevel = ORG_ROLE_LEVEL[membership.orgRole] ?: 0
        if (callerLevel <= existingLevel) {
            return Result.failure(IllegalArgumentException("Cannot modify a member at or above your own level"))
        }
        val newLevel = ORG_ROLE_LEVEL[newRole] ?: 0
        if (callerLevel <= newLevel) {
            return Result.failure(IllegalArgumentException("Cannot assign a role at or above your own level"))
        }
        if (membership.orgRole == OrgRole.OWNER) {
            val allMembers = orgMembershipRepository.findByOrganizationId(orgId)
            val ownerCount = allMembers.count { it.orgRole == OrgRole.OWNER }
            if (ownerCount <= 1) {
                return Result.failure(IllegalArgumentException("Cannot demote the last owner"))
            }
        }

        val updated = orgMembershipRepository.update(membership.copy(orgRole = newRole))
        return Result.success(updated)
    }
}

class RemoveMemberUseCase(
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val workspaceRepository: WorkspaceRepository,
) {
    fun execute(orgId: UUID, membershipId: UUID, callerId: UUID): Result<Unit> {
        val membership = orgMembershipRepository.findById(membershipId)
            ?: return Result.failure(IllegalArgumentException("Membership not found"))
        if (membership.organizationId != orgId) {
            return Result.failure(IllegalArgumentException("Membership does not belong to this organization"))
        }
        if (membership.userId == callerId) {
            return Result.failure(IllegalArgumentException("Cannot remove yourself from the organization"))
        }
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, orgId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        val callerLevel = ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0
        if (callerLevel < ORG_ROLE_LEVEL[OrgRole.ADMIN]!!) {
            return Result.failure(IllegalArgumentException("Only org admins can remove members"))
        }
        if (membership.orgRole == OrgRole.OWNER) {
            val allMembers = orgMembershipRepository.findByOrganizationId(orgId)
            val ownerCount = allMembers.count { it.orgRole == OrgRole.OWNER }
            if (ownerCount <= 1) {
                return Result.failure(IllegalArgumentException("Cannot remove the last owner"))
            }
        }

        val orgWorkspaces = workspaceRepository.findByOrganizationId(orgId)
        for (workspace in orgWorkspaces) {
            val wsMembership = workspaceMembershipRepository.findByUserAndWorkspace(membership.userId, workspace.id)
            if (wsMembership != null) {
                workspaceMembershipRepository.delete(wsMembership.id)
            }
        }

        orgMembershipRepository.delete(membershipId)
        return Result.success(Unit)
    }
}

class UpdateWorkspaceAssignmentsUseCase(
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceRepository: WorkspaceRepository,
) {
    fun execute(orgId: UUID, targetUserId: UUID, assignments: List<WorkspaceAssignment>, callerId: UUID): Result<List<WorkspaceMembership>> {
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, orgId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        val callerLevel = ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0
        if (callerLevel < ORG_ROLE_LEVEL[OrgRole.ADMIN]!!) {
            return Result.failure(IllegalArgumentException("Only org admins can manage workspace assignments"))
        }

        val orgWorkspaces = workspaceRepository.findByOrganizationId(orgId)
        val orgWorkspaceIds = orgWorkspaces.map { it.id }.toSet()
        val now = Instant.now()
        val result = mutableListOf<WorkspaceMembership>()

        for (assignment in assignments) {
            if (assignment.workspaceId !in orgWorkspaceIds) {
                return Result.failure(IllegalArgumentException("Workspace ${assignment.workspaceId} does not belong to this organization"))
            }
            val callerWsMembership = workspaceMembershipRepository.findByUserAndWorkspace(callerId, assignment.workspaceId)
            if (callerWsMembership != null) {
                val callerWsLevel = WORKSPACE_ROLE_LEVEL[callerWsMembership.workspaceRole] ?: 0
                val requestedWsLevel = WORKSPACE_ROLE_LEVEL[assignment.role] ?: 0
                if (callerWsLevel < requestedWsLevel) {
                    return Result.failure(IllegalArgumentException("Cannot assign a role at or above your own level in workspace ${assignment.workspaceId}"))
                }
            }
            val existingMembership = workspaceMembershipRepository.findByUserAndWorkspace(targetUserId, assignment.workspaceId)
            if (existingMembership != null && callerWsMembership != null) {
                val existingLevel = WORKSPACE_ROLE_LEVEL[existingMembership.workspaceRole] ?: 0
                val callerWsLevel = WORKSPACE_ROLE_LEVEL[callerWsMembership.workspaceRole] ?: 0
                if (existingLevel > callerWsLevel) {
                    return Result.failure(IllegalArgumentException("Cannot modify a membership above your level in workspace ${assignment.workspaceId}"))
                }
            }
        }

        for (assignment in assignments) {
            val existing = workspaceMembershipRepository.findByUserAndWorkspace(targetUserId, assignment.workspaceId)
            if (existing != null) {
                val updated = workspaceMembershipRepository.update(existing.copy(workspaceRole = assignment.role))
                result.add(updated)
            } else {
                val created = workspaceMembershipRepository.save(WorkspaceMembership(
                    id = UUID.randomUUID(),
                    userId = targetUserId,
                    workspaceId = assignment.workspaceId,
                    workspaceRole = assignment.role,
                    addedAt = now,
                ))
                result.add(created)
            }
        }

        val targetMemberships = workspaceMembershipRepository.findByUserId(targetUserId)
            .filter { it.workspaceId in orgWorkspaceIds }
        for (membership in targetMemberships) {
            if (membership.workspaceId !in assignments.map { it.workspaceId }.toSet()) {
                val callerWsMembership = workspaceMembershipRepository.findByUserAndWorkspace(callerId, membership.workspaceId)
                if (callerWsMembership != null) {
                    val callerWsLevel = WORKSPACE_ROLE_LEVEL[callerWsMembership.workspaceRole] ?: 0
                    val existingLevel = WORKSPACE_ROLE_LEVEL[membership.workspaceRole] ?: 0
                    if (existingLevel <= callerWsLevel) {
                        workspaceMembershipRepository.delete(membership.id)
                    }
                }
            }
        }

        return Result.success(result)
    }
}
