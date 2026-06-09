package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class MemberManagementUseCasesTest {

    private lateinit var orgMembershipRepo: InMemoryOrgMembershipRepository
    private lateinit var workspaceMembershipRepo: InMemoryWorkspaceMembershipRepository
    private lateinit var workspaceRepo: InMemoryWorkspaceRepository
    private lateinit var updateRoleUseCase: UpdateMemberOrgRoleUseCase
    private lateinit var removeMemberUseCase: RemoveMemberUseCase
    private lateinit var updateWsAssignmentsUseCase: UpdateWorkspaceAssignmentsUseCase

    private val orgId = UUID.randomUUID()
    private val ownerId = UUID.randomUUID()
    private val owner2Id = UUID.randomUUID()
    private val adminId = UUID.randomUUID()
    private val memberId = UUID.randomUUID()
    private val workspaceId = UUID.randomUUID()

    private lateinit var ownerMembership: OrgMembership
    private lateinit var owner2Membership: OrgMembership
    private lateinit var adminMembership: OrgMembership
    private lateinit var memberMembership: OrgMembership

    @BeforeEach
    fun setUp() {
        orgMembershipRepo = InMemoryOrgMembershipRepository()
        workspaceMembershipRepo = InMemoryWorkspaceMembershipRepository()
        workspaceRepo = InMemoryWorkspaceRepository()
        updateRoleUseCase = UpdateMemberOrgRoleUseCase(orgMembershipRepo)
        removeMemberUseCase = RemoveMemberUseCase(orgMembershipRepo, workspaceMembershipRepo, workspaceRepo)
        updateWsAssignmentsUseCase = UpdateWorkspaceAssignmentsUseCase(workspaceMembershipRepo, orgMembershipRepo, workspaceRepo)

        val now = Instant.now()
        ownerMembership = orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), ownerId, orgId, OrgRole.OWNER, now, now))
        owner2Membership = orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), owner2Id, orgId, OrgRole.OWNER, now, now))
        adminMembership = orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), adminId, orgId, OrgRole.ADMIN, now, now))
        memberMembership = orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), memberId, orgId, OrgRole.MEMBER, now, now))

        workspaceRepo.save(Workspace(
            id = workspaceId, organizationId = orgId, name = "WS", slug = "ws",
            ownerId = ownerId, settings = WorkspaceSettings(), createdAt = now, updatedAt = now,
        ))
        workspaceMembershipRepo.save(WorkspaceMembership(UUID.randomUUID(), adminId, workspaceId, WorkspaceRole.MANAGER, addedAt = now))
        workspaceMembershipRepo.save(WorkspaceMembership(UUID.randomUUID(), memberId, workspaceId, WorkspaceRole.VIEWER, addedAt = now))
    }

    @Test
    fun `UpdateMemberOrgRole success`() {
        val result = updateRoleUseCase.execute(orgId, memberMembership.id, OrgRole.ADMIN, ownerId)
        assertTrue(result.isSuccess)
        assertEquals(OrgRole.ADMIN, result.getOrThrow().orgRole)
    }

    @Test
    fun `UpdateMemberOrgRole fails if not admin`() {
        val result = updateRoleUseCase.execute(orgId, memberMembership.id, OrgRole.ADMIN, memberId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Only org admins"))
    }

    @Test
    fun `UpdateMemberOrgRole fails if promoting to OWNER`() {
        val result = updateRoleUseCase.execute(orgId, memberMembership.id, OrgRole.OWNER, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("owner"))
    }

    @Test
    fun `UpdateMemberOrgRole fails if modifying someone at or above own level`() {
        val result = updateRoleUseCase.execute(orgId, owner2Membership.id, OrgRole.MEMBER, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("at or above your own level"))
    }

    @Test
    fun `UpdateMemberOrgRole fails if owner tries to demote self`() {
        val result = updateRoleUseCase.execute(orgId, ownerMembership.id, OrgRole.ADMIN, ownerId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("at or above your own level"))
    }

    @Test
    fun `UpdateMemberOrgRole fails if admin promotes member to admin at same level`() {
        val result = updateRoleUseCase.execute(orgId, memberMembership.id, OrgRole.ADMIN, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("at or above your own level"))
    }

    @Test
    fun `RemoveMember success`() {
        val result = removeMemberUseCase.execute(orgId, memberMembership.id, adminId)
        assertTrue(result.isSuccess)
        assertNull(orgMembershipRepo.findById(memberMembership.id))
    }

    @Test
    fun `RemoveMember fails if removing self`() {
        val result = removeMemberUseCase.execute(orgId, adminMembership.id, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("yourself"))
    }

    @Test
    fun `RemoveMember fails if removing last owner`() {
        val soleOrgId = UUID.randomUUID()
        val soleOwnerId = UUID.randomUUID()
        val soleAdminId = UUID.randomUUID()
        val now = Instant.now()
        val soleOwner = orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), soleOwnerId, soleOrgId, OrgRole.OWNER, now, now))
        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), soleAdminId, soleOrgId, OrgRole.ADMIN, now, now))
        val result = removeMemberUseCase.execute(soleOrgId, soleOwner.id, soleAdminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("last owner"))
    }

    @Test
    fun `RemoveMember removes workspace memberships`() {
        val result = removeMemberUseCase.execute(orgId, memberMembership.id, adminId)
        assertTrue(result.isSuccess)
        assertNull(workspaceMembershipRepo.findByUserAndWorkspace(memberId, workspaceId))
    }

    @Test
    fun `UpdateWorkspaceAssignments success`() {
        val result = updateWsAssignmentsUseCase.execute(orgId, memberId, listOf(WorkspaceAssignment(workspaceId, WorkspaceRole.EDITOR)), adminId)
        assertTrue(result.isSuccess)
        assertEquals(1, result.getOrThrow().size)
        assertEquals(WorkspaceRole.EDITOR, result.getOrThrow()[0].workspaceRole)
    }

    @Test
    fun `UpdateWorkspaceAssignments fails if workspace not in org`() {
        val otherWorkspaceId = UUID.randomUUID()
        val result = updateWsAssignmentsUseCase.execute(orgId, memberId, listOf(WorkspaceAssignment(otherWorkspaceId, WorkspaceRole.VIEWER)), adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("does not belong"))
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

    private class InMemoryWorkspaceRepository : WorkspaceRepository {
        private val workspaces = mutableMapOf<UUID, Workspace>()
        override fun findById(id: UUID) = workspaces[id]
        override fun findBySlug(slug: String) = workspaces.values.find { it.slug == slug }
        override fun findByOrganizationId(organizationId: UUID) = workspaces.values.filter { it.organizationId == organizationId }
        override fun save(workspace: Workspace) = workspace.also { workspaces[it.id] = it }
        override fun delete(id: UUID) { workspaces.remove(id) }
    }
}
