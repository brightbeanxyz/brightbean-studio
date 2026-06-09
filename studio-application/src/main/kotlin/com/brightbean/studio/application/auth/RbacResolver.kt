package com.brightbean.studio.application.auth

import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.model.WorkspaceMembership
import com.brightbean.studio.domain.repository.CustomRoleRepository
import com.brightbean.studio.domain.repository.OrgMembershipRepository
import com.brightbean.studio.domain.repository.WorkspaceMembershipRepository
import java.util.UUID

class RbacResolver(
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val customRoleRepository: CustomRoleRepository,
) {
    fun resolve(user: User, workspaceId: UUID? = null, orgId: UUID? = null): RbacContext {
        val orgMembership = if (orgId != null) {
            orgMembershipRepository.findByUserAndOrganization(user.id, orgId)
        } else {
            orgMembershipRepository.findByUserId(user.id).firstOrNull()
        }

        val workspaceMembership = if (workspaceId != null) {
            workspaceMembershipRepository.findByUserAndWorkspace(user.id, workspaceId)
        } else null

        val effectivePermissions = resolvePermissions(workspaceMembership)

        return RbacContext(
            user = user,
            orgMembership = orgMembership,
            workspaceMembership = workspaceMembership,
            effectivePermissions = effectivePermissions,
        )
    }

    private fun resolvePermissions(membership: WorkspaceMembership?): Map<String, Boolean> {
        if (membership == null) return emptyMap()

        val customRoleId = membership.customRoleId
        if (customRoleId != null) {
            val customRole = customRoleRepository.findById(customRoleId)
            if (customRole != null) return customRole.permissions
        }

        return (BUILTIN_WORKSPACE_PERMISSIONS[membership.workspaceRole] ?: emptySet())
            .associateWith { true }
    }
}
