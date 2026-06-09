package com.brightbean.studio.application.usecase

import com.brightbean.studio.application.auth.ORG_ROLE_LEVEL
import com.brightbean.studio.application.auth.WORKSPACE_ROLE_LEVEL
import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import java.time.Instant
import java.util.UUID

data class WorkspaceAssignment(val workspaceId: UUID, val role: WorkspaceRole)

class CreateInvitationUseCase(
    private val invitationRepository: InvitationRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val userRepository: UserRepository,
) {
    private val gson = Gson()

    fun execute(orgId: UUID, email: String, orgRole: OrgRole, workspaceAssignments: List<WorkspaceAssignment>, invitedBy: UUID): Result<Invitation> {
        val inviterMembership = orgMembershipRepository.findByUserAndOrganization(invitedBy, orgId)
            ?: return Result.failure(IllegalArgumentException("Inviter is not a member of this organization"))
        val inviterLevel = ORG_ROLE_LEVEL[inviterMembership.orgRole] ?: 0
        if (inviterLevel < ORG_ROLE_LEVEL[OrgRole.ADMIN]!!) {
            return Result.failure(IllegalArgumentException("Only org admins can send invitations"))
        }
        if (orgRole == OrgRole.OWNER) {
            return Result.failure(IllegalArgumentException("Cannot invite someone as organization owner"))
        }
        val requestedLevel = ORG_ROLE_LEVEL[orgRole] ?: 0
        if (inviterLevel < requestedLevel) {
            return Result.failure(IllegalArgumentException("Cannot invite someone at or above your own role level"))
        }
        val existingMembers = orgMembershipRepository.findByOrganizationId(orgId)
        for (membership in existingMembers) {
            val user = userRepository.findById(membership.userId)
            if (user?.email?.equals(email, ignoreCase = true) == true) {
                return Result.failure(IllegalArgumentException("User is already a member of this organization"))
            }
        }
        val existingInvites = invitationRepository.findByOrganizationId(orgId)
        if (existingInvites.any { it.email.equals(email, ignoreCase = true) && it.status == InvitationStatus.PENDING }) {
            return Result.failure(IllegalArgumentException("A pending invitation already exists for this email"))
        }
        for (assignment in workspaceAssignments) {
            val inviterWsMembership = workspaceMembershipRepository.findByUserAndWorkspace(invitedBy, assignment.workspaceId)
            if (inviterWsMembership == null) {
                return Result.failure(IllegalArgumentException("Inviter is not a member of workspace ${assignment.workspaceId}"))
            }
            val inviterWsLevel = WORKSPACE_ROLE_LEVEL[inviterWsMembership.workspaceRole] ?: 0
            val requestedWsLevel = WORKSPACE_ROLE_LEVEL[assignment.role] ?: 0
            if (inviterWsLevel < requestedWsLevel) {
                return Result.failure(IllegalArgumentException("Cannot assign a workspace role at or above your own level"))
            }
        }

        val now = Instant.now()
        val token = UUID.randomUUID().toString()
        val assignmentsJson = gson.toJson(workspaceAssignments.map { mapOf("workspaceId" to it.workspaceId.toString(), "role" to it.role.name) })
        val invitation = Invitation(
            id = UUID.randomUUID(),
            organizationId = orgId,
            email = email,
            orgRole = orgRole,
            workspaceAssignments = assignmentsJson,
            invitedBy = invitedBy,
            token = token,
            expiresAt = now.plusSeconds(7 * 24 * 3600),
            status = InvitationStatus.PENDING,
            createdAt = now,
        )
        val saved = invitationRepository.save(invitation)
        return Result.success(saved)
    }
}

class AcceptInvitationUseCase(
    private val invitationRepository: InvitationRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
    private val workspaceMembershipRepository: WorkspaceMembershipRepository,
    private val userRepository: UserRepository,
) {
    private val gson = Gson()

    fun execute(token: String, userId: UUID): Result<OrgMembership> {
        val invitation = invitationRepository.findByToken(token)
            ?: return Result.failure(IllegalArgumentException("Invitation not found"))

        if (invitation.status != InvitationStatus.PENDING) {
            return Result.failure(IllegalArgumentException("Invitation is no longer pending"))
        }
        if (invitation.expiresAt.isBefore(Instant.now())) {
            return Result.failure(IllegalArgumentException("Invitation has expired"))
        }

        val now = Instant.now()

        val orgMembership = OrgMembership(
            id = UUID.randomUUID(),
            userId = userId,
            organizationId = invitation.organizationId,
            orgRole = invitation.orgRole,
            invitedAt = invitation.createdAt,
            acceptedAt = now,
        )
        orgMembershipRepository.save(orgMembership)

        val type = object : TypeToken<List<Map<String, String>>>() {}.type
        val assignments: List<Map<String, String>> = gson.fromJson(invitation.workspaceAssignments, type)
        for (assignment in assignments) {
            val wsId = UUID.fromString(assignment["workspaceId"])
            val role = WorkspaceRole.valueOf(assignment["role"]!!)
            val wsMembership = WorkspaceMembership(
                id = UUID.randomUUID(),
                userId = userId,
                workspaceId = wsId,
                workspaceRole = role,
                addedAt = now,
            )
            workspaceMembershipRepository.save(wsMembership)
        }

        invitationRepository.update(invitation.copy(
            status = InvitationStatus.ACCEPTED,
            acceptedAt = now,
        ))

        return Result.success(orgMembership)
    }
}

class ResendInvitationUseCase(
    private val invitationRepository: InvitationRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(invitationId: UUID, callerId: UUID): Result<Invitation> {
        val invitation = invitationRepository.findById(invitationId)
            ?: return Result.failure(IllegalArgumentException("Invitation not found"))
        if (invitation.status == InvitationStatus.ACCEPTED) {
            return Result.failure(IllegalArgumentException("Cannot resend an accepted invitation"))
        }
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, invitation.organizationId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        if ((ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0) < (ORG_ROLE_LEVEL[OrgRole.ADMIN] ?: 0)) {
            return Result.failure(IllegalArgumentException("Only org admins can resend invitations"))
        }

        val updated = invitation.copy(
            token = UUID.randomUUID().toString(),
            expiresAt = Instant.now().plusSeconds(7 * 24 * 3600),
            status = InvitationStatus.PENDING,
        )
        return Result.success(invitationRepository.update(updated))
    }
}

class RevokeInvitationUseCase(
    private val invitationRepository: InvitationRepository,
    private val orgMembershipRepository: OrgMembershipRepository,
) {
    fun execute(invitationId: UUID, callerId: UUID): Result<Invitation> {
        val invitation = invitationRepository.findById(invitationId)
            ?: return Result.failure(IllegalArgumentException("Invitation not found"))
        if (invitation.status == InvitationStatus.ACCEPTED) {
            return Result.failure(IllegalArgumentException("Cannot revoke an accepted invitation"))
        }
        val callerMembership = orgMembershipRepository.findByUserAndOrganization(callerId, invitation.organizationId)
            ?: return Result.failure(IllegalArgumentException("Caller is not a member of this organization"))
        if ((ORG_ROLE_LEVEL[callerMembership.orgRole] ?: 0) < (ORG_ROLE_LEVEL[OrgRole.ADMIN] ?: 0)) {
            return Result.failure(IllegalArgumentException("Only org admins can revoke invitations"))
        }

        val updated = invitation.copy(status = InvitationStatus.REVOKED)
        return Result.success(invitationRepository.update(updated))
    }
}
