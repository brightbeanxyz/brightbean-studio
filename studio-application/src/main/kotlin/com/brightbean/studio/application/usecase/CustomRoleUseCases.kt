package com.brightbean.studio.application.usecase

import com.brightbean.studio.application.auth.ORG_ROLE_LEVEL
import com.brightbean.studio.application.auth.WorkspacePermissionKeys
import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import java.time.Instant
import java.util.UUID

class CreateCustomRoleUseCase(
    private val customRoleRepository: CustomRoleRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(orgId: UUID, name: String, permissions: Map<String, Boolean>, callerId: UUID): Result<CustomRole> {
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, orgId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        if ((ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0) < (ORG_ROLE_LEVEL[OrgRole.ADMIN] ?: 0)) {
            return Result.failure(IllegalArgumentException("Only org admins can create custom roles"))
        }
        val invalidKeys = permissions.keys.filter { it !in WorkspacePermissionKeys.ALL }
        if (invalidKeys.isNotEmpty()) {
            return Result.failure(IllegalArgumentException("Invalid permission keys: $invalidKeys"))
        }

        val now = Instant.now()
        val role = CustomRole(
            id = UUID.randomUUID(),
            organizationId = orgId,
            name = name,
            permissions = permissions,
            createdAt = now,
            updatedAt = now,
        )
        return Result.success(customRoleRepository.save(role))
    }
}

class UpdateCustomRoleUseCase(
    private val customRoleRepository: CustomRoleRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(roleId: UUID, name: String? = null, permissions: Map<String, Boolean>? = null, callerId: UUID): Result<CustomRole> {
        val role = customRoleRepository.findById(roleId)
            ?: return Result.failure(IllegalArgumentException("Custom role not found"))
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, role.organizationId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        if ((ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0) < (ORG_ROLE_LEVEL[OrgRole.ADMIN] ?: 0)) {
            return Result.failure(IllegalArgumentException("Only org admins can update custom roles"))
        }
        if (permissions != null) {
            val invalidKeys = permissions.keys.filter { it !in WorkspacePermissionKeys.ALL }
            if (invalidKeys.isNotEmpty()) {
                return Result.failure(IllegalArgumentException("Invalid permission keys: $invalidKeys"))
            }
        }

        val updated = role.copy(
            name = name ?: role.name,
            permissions = permissions ?: role.permissions,
            updatedAt = Instant.now(),
        )
        return Result.success(customRoleRepository.update(updated))
    }
}

class DeleteCustomRoleUseCase(
    private val customRoleRepository: CustomRoleRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(roleId: UUID, callerId: UUID): Result<Unit> {
        val role = customRoleRepository.findById(roleId)
            ?: return Result.failure(IllegalArgumentException("Custom role not found"))
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, role.organizationId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        if ((ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0) < (ORG_ROLE_LEVEL[OrgRole.ADMIN] ?: 0)) {
            return Result.failure(IllegalArgumentException("Only org admins can delete custom roles"))
        }

        customRoleRepository.delete(roleId)
        return Result.success(Unit)
    }
}
