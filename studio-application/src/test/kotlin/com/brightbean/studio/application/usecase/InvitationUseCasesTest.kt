package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class InvitationUseCasesTest {

    private lateinit var invitationRepo: InMemoryInvitationRepository
    private lateinit var orgMembershipRepo: InMemoryOrgMembershipRepository
    private lateinit var workspaceMembershipRepo: InMemoryWorkspaceMembershipRepository
    private lateinit var userRepo: InMemoryUserRepository
    private lateinit var createUseCase: CreateInvitationUseCase
    private lateinit var acceptUseCase: AcceptInvitationUseCase
    private lateinit var resendUseCase: ResendInvitationUseCase
    private lateinit var revokeUseCase: RevokeInvitationUseCase

    private val orgId = UUID.randomUUID()
    private val ownerId = UUID.randomUUID()
    private val adminId = UUID.randomUUID()
    private val memberId = UUID.randomUUID()
    private val newUserId = UUID.randomUUID()
    private val workspaceId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        invitationRepo = InMemoryInvitationRepository()
        orgMembershipRepo = InMemoryOrgMembershipRepository()
        workspaceMembershipRepo = InMemoryWorkspaceMembershipRepository()
        userRepo = InMemoryUserRepository()
        createUseCase = CreateInvitationUseCase(invitationRepo, orgMembershipRepo, workspaceMembershipRepo, userRepo)
        acceptUseCase = AcceptInvitationUseCase(invitationRepo, orgMembershipRepo, workspaceMembershipRepo, userRepo)
        resendUseCase = ResendInvitationUseCase(invitationRepo, orgMembershipRepo)
        revokeUseCase = RevokeInvitationUseCase(invitationRepo, orgMembershipRepo)

        val now = Instant.now()
        userRepo.save(User(ownerId, "owner@example.com", "Owner", "hash", createdAt = now, updatedAt = now))
        userRepo.save(User(adminId, "admin@example.com", "Admin", "hash", createdAt = now, updatedAt = now))
        userRepo.save(User(memberId, "member@example.com", "Member", "hash", createdAt = now, updatedAt = now))
        userRepo.save(User(newUserId, "new@example.com", "New User", "hash", createdAt = now, updatedAt = now))

        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), ownerId, orgId, OrgRole.OWNER, now, now))
        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), adminId, orgId, OrgRole.ADMIN, now, now))
        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), memberId, orgId, OrgRole.MEMBER, now, now))

        workspaceMembershipRepo.save(WorkspaceMembership(UUID.randomUUID(), ownerId, workspaceId, WorkspaceRole.OWNER, addedAt = now))
        workspaceMembershipRepo.save(WorkspaceMembership(UUID.randomUUID(), adminId, workspaceId, WorkspaceRole.MANAGER, addedAt = now))
    }

    @Test
    fun `CreateInvitation success with valid data`() {
        val result = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, listOf(WorkspaceAssignment(workspaceId, WorkspaceRole.EDITOR)), adminId)
        assertTrue(result.isSuccess)
        val invitation = result.getOrThrow()
        assertEquals("invite@example.com", invitation.email)
        assertEquals(OrgRole.MEMBER, invitation.orgRole)
        assertEquals(InvitationStatus.PENDING, invitation.status)
    }

    @Test
    fun `CreateInvitation fails if inviter not org member`() {
        val result = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), UUID.randomUUID())
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("not a member"))
    }

    @Test
    fun `CreateInvitation fails if inviter is not admin`() {
        val result = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), memberId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Only org admins"))
    }

    @Test
    fun `CreateInvitation fails if trying to invite as OWNER`() {
        val result = createUseCase.execute(orgId, "invite@example.com", OrgRole.OWNER, emptyList(), adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("owner"))
    }

    @Test
    fun `CreateInvitation fails if email already org member`() {
        val result = createUseCase.execute(orgId, "member@example.com", OrgRole.MEMBER, emptyList(), adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("already a member"))
    }

    @Test
    fun `CreateInvitation fails if pending invite already exists`() {
        createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), adminId)
        val result = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("pending invitation already exists"))
    }

    @Test
    fun `AcceptInvitation success`() {
        val invitation = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, listOf(WorkspaceAssignment(workspaceId, WorkspaceRole.EDITOR)), adminId).getOrThrow()
        val result = acceptUseCase.execute(invitation.token, newUserId)
        assertTrue(result.isSuccess)
        val membership = result.getOrThrow()
        assertEquals(OrgRole.MEMBER, membership.orgRole)
        assertEquals(newUserId, membership.userId)

        val wsMembership = workspaceMembershipRepo.findByUserAndWorkspace(newUserId, workspaceId)
        assertNotNull(wsMembership)
        assertEquals(WorkspaceRole.EDITOR, wsMembership!!.workspaceRole)
    }

    @Test
    fun `AcceptInvitation fails if invitation not found`() {
        val result = acceptUseCase.execute("nonexistent-token", newUserId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("not found"))
    }

    @Test
    fun `AcceptInvitation fails if invitation expired`() {
        val now = Instant.now()
        val expired = Invitation(
            id = UUID.randomUUID(),
            organizationId = orgId,
            email = "invite@example.com",
            orgRole = OrgRole.MEMBER,
            workspaceAssignments = "[]",
            invitedBy = adminId,
            token = "expired-token",
            expiresAt = now.minusSeconds(1),
            status = InvitationStatus.PENDING,
            createdAt = now,
        )
        invitationRepo.save(expired)

        val result = acceptUseCase.execute("expired-token", newUserId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("expired"))
    }

    @Test
    fun `AcceptInvitation fails if invitation already accepted`() {
        val now = Instant.now()
        val accepted = Invitation(
            id = UUID.randomUUID(),
            organizationId = orgId,
            email = "invite@example.com",
            orgRole = OrgRole.MEMBER,
            workspaceAssignments = "[]",
            invitedBy = adminId,
            token = "accepted-token",
            expiresAt = now.plusSeconds(99999),
            status = InvitationStatus.ACCEPTED,
            createdAt = now,
        )
        invitationRepo.save(accepted)

        val result = acceptUseCase.execute("accepted-token", newUserId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("no longer pending"))
    }

    @Test
    fun `ResendInvitation success`() {
        val invitation = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), adminId).getOrThrow()
        val result = resendUseCase.execute(invitation.id, adminId)
        assertTrue(result.isSuccess)
        assertNotEquals(invitation.token, result.getOrThrow().token)
    }

    @Test
    fun `ResendInvitation fails if accepted`() {
        val invitation = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), adminId).getOrThrow()
        acceptUseCase.execute(invitation.token, newUserId)

        val result = resendUseCase.execute(invitation.id, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("accepted"))
    }

    @Test
    fun `RevokeInvitation success`() {
        val invitation = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), adminId).getOrThrow()
        val result = revokeUseCase.execute(invitation.id, adminId)
        assertTrue(result.isSuccess)
        assertEquals(InvitationStatus.REVOKED, result.getOrThrow().status)
    }

    @Test
    fun `RevokeInvitation fails if accepted`() {
        val invitation = createUseCase.execute(orgId, "invite@example.com", OrgRole.MEMBER, emptyList(), adminId).getOrThrow()
        acceptUseCase.execute(invitation.token, newUserId)

        val result = revokeUseCase.execute(invitation.id, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("accepted"))
    }

    private class InMemoryInvitationRepository : InvitationRepository {
        private val items = mutableMapOf<UUID, Invitation>()
        override fun findById(id: UUID) = items[id]
        override fun findByToken(token: String) = items.values.find { it.token == token }
        override fun findByOrganizationId(organizationId: UUID) = items.values.filter { it.organizationId == organizationId }
        override fun save(invitation: Invitation) = invitation.also { items[it.id] = it }
        override fun update(invitation: Invitation) = invitation.also { items[it.id] = it }
        override fun delete(id: UUID) { items.remove(id) }
    }

    private class InMemoryOrgMembershipRepository : OrgMembershipRepository {
        private val memberships = mutableMapOf<UUID, OrgMembership>()
        override fun findById(id: UUID) = memberships[id]
        override fun findByUserId(userId: UUID) = memberships.values.filter { it.userId == userId }
        override fun findByOrganizationId(organizationId: UUID) = memberships.values.filter { it.organizationId == organizationId }
        override fun findByUserAndOrganization(userId: UUID, organizationId: UUID) =
            memberships.values.find { it.userId == userId && it.organizationId == organizationId }
        override fun save(membership: OrgMembership) = membership.also { memberships[membership.id] = it }
        override fun update(membership: OrgMembership) = membership.also { memberships[membership.id] = it }
        override fun delete(id: UUID) { memberships.remove(id) }
    }

    private class InMemoryWorkspaceMembershipRepository : WorkspaceMembershipRepository {
        private val memberships = mutableMapOf<UUID, WorkspaceMembership>()
        override fun findById(id: UUID) = memberships[id]
        override fun findByUserId(userId: UUID) = memberships.values.filter { it.userId == userId }
        override fun findByWorkspaceId(workspaceId: UUID) = memberships.values.filter { it.workspaceId == workspaceId }
        override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID) =
            memberships.values.find { it.userId == userId && it.workspaceId == workspaceId }
        override fun save(membership: WorkspaceMembership) = membership.also { memberships[membership.id] = it }
        override fun update(membership: WorkspaceMembership) = membership.also { memberships[membership.id] = it }
        override fun delete(id: UUID) { memberships.remove(id) }
    }

    private class InMemoryUserRepository : UserRepository {
        private val users = mutableMapOf<UUID, User>()
        override fun findById(id: UUID) = users[id]
        override fun findByEmail(email: String) = users.values.find { it.email == email }
        override fun save(user: User) = user.also { users[user.id] = it }
        override fun update(user: User) = user.also { users[user.id] = it }
        override fun delete(id: UUID) { users.remove(id) }
    }
}
