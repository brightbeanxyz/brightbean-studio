package com.brightbean.studio.application.usecase

import com.brightbean.studio.application.auth.ORG_ROLE_LEVEL
import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import java.time.Instant
import java.util.UUID

class CreateOrganizationUseCase(
    private val organizationRepository: OrganizationRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceRepository: WorkspaceRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
) {
    fun execute(userId: UUID, name: String, defaultTimezone: String = "UTC"): Result<Organization> {
        val now = Instant.now()
        val org = Organization(
            id = UUID.randomUUID(),
            name = name,
            defaultTimezone = defaultTimezone,
            createdAt = now,
            updatedAt = now,
        )
        organizationRepository.save(org)

        val orgMembership = OrgMembership(
            id = UUID.randomUUID(),
            userId = userId,
            organizationId = org.id,
            orgRole = OrgRole.OWNER,
            invitedAt = now,
            acceptedAt = now,
        )
        orgMembershipRepository.save(orgMembership)

        val slug = name.lowercase().replace(Regex("[^a-z0-9]+"), "-").trim('-')
        val workspace = Workspace(
            id = UUID.randomUUID(),
            organizationId = org.id,
            name = name,
            slug = if (slug.isNotBlank()) slug else UUID.randomUUID().toString().substring(0, 8),
            ownerId = userId,
            settings = WorkspaceSettings(),
            isArchived = false,
            createdAt = now,
            updatedAt = now,
        )
        workspaceRepository.save(workspace)

        val wsMembership = WorkspaceMembership(
            id = UUID.randomUUID(),
            userId = userId,
            workspaceId = workspace.id,
            workspaceRole = WorkspaceRole.OWNER,
            addedAt = now,
        )
        workspaceMembershipRepository.save(wsMembership)

        return Result.success(org)
    }
}

class UpdateOrganizationUseCase(
    private val organizationRepository: OrganizationRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(orgId: UUID, name: String? = null, defaultTimezone: String? = null, callerId: UUID): Result<Organization> {
        val org = organizationRepository.findById(orgId)
            ?: return Result.failure(IllegalArgumentException("Organization not found"))
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, orgId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        val callerLevel = ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0
        if (callerLevel < ORG_ROLE_LEVEL[OrgRole.ADMIN]!!) {
            return Result.failure(IllegalArgumentException("Only org admins can update organization settings"))
        }

        val updated = org.copy(
            name = name ?: org.name,
            defaultTimezone = defaultTimezone ?: org.defaultTimezone,
            updatedAt = Instant.now(),
        )
        return Result.success(organizationRepository.update(updated))
    }
}
