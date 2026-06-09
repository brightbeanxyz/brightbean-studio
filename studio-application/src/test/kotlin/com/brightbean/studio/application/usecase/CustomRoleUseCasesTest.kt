package com.brightbean.studio.application.usecase

import com.brightbean.studio.application.auth.WorkspacePermissionKeys
import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class CustomRoleUseCasesTest {

    private lateinit var customRoleRepo: InMemoryCustomRoleRepository
    private lateinit var orgMembershipRepo: InMemoryOrgMembershipRepository
    private lateinit var workspaceMembershipRepo: InMemoryWorkspaceMembershipRepository
    private lateinit var createUseCase: CreateCustomRoleUseCase
    private lateinit var updateUseCase: UpdateCustomRoleUseCase
    private lateinit var deleteUseCase: DeleteCustomRoleUseCase

    private val orgId = UUID.randomUUID()
    private val adminId = UUID.randomUUID()
    private val memberId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        customRoleRepo = InMemoryCustomRoleRepository()
        orgMembershipRepo = InMemoryOrgMembershipRepository()
        workspaceMembershipRepo = InMemoryWorkspaceMembershipRepository()
        createUseCase = CreateCustomRoleUseCase(customRoleRepo, orgMembershipRepo)
        updateUseCase = UpdateCustomRoleUseCase(customRoleRepo, orgMembershipRepo)
        deleteUseCase = DeleteCustomRoleUseCase(customRoleRepo, workspaceMembershipRepo, orgMembershipRepo)

        val now = Instant.now()
        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), adminId, orgId, OrgRole.ADMIN, now, now))
        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), memberId, orgId, OrgRole.MEMBER, now, now))
    }

    @Test
    fun `CreateCustomRole success`() {
        val permissions = mapOf(
            WorkspacePermissionKeys.CREATE_POSTS to true,
            WorkspacePermissionKeys.VIEW_ANALYTICS to true,
        )
        val result = createUseCase.execute(orgId, "Custom Editor", permissions, adminId)
        assertTrue(result.isSuccess)
        val role = result.getOrThrow()
        assertEquals("Custom Editor", role.name)
        assertEquals(orgId, role.organizationId)
        assertEquals(2, role.permissions.size)
    }

    @Test
    fun `CreateCustomRole fails with invalid permission key`() {
        val permissions = mapOf("invalid_permission" to true)
        val result = createUseCase.execute(orgId, "Bad Role", permissions, adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Invalid permission keys"))
    }

    @Test
    fun `CreateCustomRole fails if not admin`() {
        val permissions = mapOf(WorkspacePermissionKeys.CREATE_POSTS to true)
        val result = createUseCase.execute(orgId, "Role", permissions, memberId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Only org admins"))
    }

    @Test
    fun `UpdateCustomRole success`() {
        val role = createUseCase.execute(orgId, "Old Name", mapOf(WorkspacePermissionKeys.CREATE_POSTS to true), adminId).getOrThrow()
        val result = updateUseCase.execute(role.id, name = "New Name", callerId = adminId)
        assertTrue(result.isSuccess)
        assertEquals("New Name", result.getOrThrow().name)
    }

    @Test
    fun `UpdateCustomRole success with new permissions`() {
        val role = createUseCase.execute(orgId, "Role", mapOf(WorkspacePermissionKeys.CREATE_POSTS to true), adminId).getOrThrow()
        val newPerms = mapOf(WorkspacePermissionKeys.VIEW_ANALYTICS to true, WorkspacePermissionKeys.USE_INBOX to true)
        val result = updateUseCase.execute(role.id, permissions = newPerms, callerId = adminId)
        assertTrue(result.isSuccess)
        assertEquals(2, result.getOrThrow().permissions.size)
    }

    @Test
    fun `UpdateCustomRole fails with invalid permission keys`() {
        val role = createUseCase.execute(orgId, "Role", mapOf(WorkspacePermissionKeys.CREATE_POSTS to true), adminId).getOrThrow()
        val result = updateUseCase.execute(role.id, permissions = mapOf("bogus" to true), callerId = adminId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Invalid permission keys"))
    }

    @Test
    fun `DeleteCustomRole success`() {
        val role = createUseCase.execute(orgId, "Role", mapOf(WorkspacePermissionKeys.CREATE_POSTS to true), adminId).getOrThrow()
        val result = deleteUseCase.execute(role.id, adminId)
        assertTrue(result.isSuccess)
        assertNull(customRoleRepo.findById(role.id))
    }

    @Test
    fun `DeleteCustomRole fails if not admin`() {
        val role = createUseCase.execute(orgId, "Role", mapOf(WorkspacePermissionKeys.CREATE_POSTS to true), adminId).getOrThrow()
        val result = deleteUseCase.execute(role.id, memberId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Only org admins"))
    }

    private class InMemoryCustomRoleRepository : CustomRoleRepository {
        private val roles = mutableMapOf<UUID, CustomRole>()
        override fun findById(id: UUID) = roles[id]
        override fun findByOrganizationId(organizationId: UUID) = roles.values.filter { it.organizationId == organizationId }
        override fun save(customRole: CustomRole) = customRole.also { roles[it.id] = it }
        override fun update(customRole: CustomRole) = customRole.also { roles[it.id] = it }
        override fun delete(id: UUID) { roles.remove(id) }
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
}
