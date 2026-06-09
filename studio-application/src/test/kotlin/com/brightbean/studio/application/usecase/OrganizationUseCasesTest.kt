package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.*
import com.brightbean.studio.domain.repository.*
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class OrganizationUseCasesTest {

    private lateinit var organizationRepo: InMemoryOrganizationRepository
    private lateinit var orgMembershipRepo: InMemoryOrgMembershipRepository
    private lateinit var workspaceRepo: InMemoryWorkspaceRepository
    private lateinit var workspaceMembershipRepo: InMemoryWorkspaceMembershipRepository
    private lateinit var createUseCase: CreateOrganizationUseCase
    private lateinit var updateUseCase: UpdateOrganizationUseCase

    private val ownerId = UUID.randomUUID()
    private val adminId = UUID.randomUUID()
    private val memberId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        organizationRepo = InMemoryOrganizationRepository()
        orgMembershipRepo = InMemoryOrgMembershipRepository()
        workspaceRepo = InMemoryWorkspaceRepository()
        workspaceMembershipRepo = InMemoryWorkspaceMembershipRepository()
        createUseCase = CreateOrganizationUseCase(organizationRepo, orgMembershipRepo, workspaceRepo, workspaceMembershipRepo)
        updateUseCase = UpdateOrganizationUseCase(organizationRepo, orgMembershipRepo)
    }

    @Test
    fun `CreateOrganization success creates org and workspace and memberships`() {
        val result = createUseCase.execute(ownerId, "Test Org", "UTC")
        assertTrue(result.isSuccess)
        val org = result.getOrThrow()
        assertEquals("Test Org", org.name)

        val memberships = orgMembershipRepo.findByOrganizationId(org.id)
        assertEquals(1, memberships.size)
        assertEquals(OrgRole.OWNER, memberships[0].orgRole)
        assertEquals(ownerId, memberships[0].userId)

        val workspaces = workspaceRepo.findByOrganizationId(org.id)
        assertEquals(1, workspaces.size)
        assertEquals("Test Org", workspaces[0].name)
        assertEquals(ownerId, workspaces[0].ownerId)

        val wsMemberships = workspaceMembershipRepo.findByWorkspaceId(workspaces[0].id)
        assertEquals(1, wsMemberships.size)
        assertEquals(WorkspaceRole.OWNER, wsMemberships[0].workspaceRole)
    }

    @Test
    fun `UpdateOrganization success`() {
        val org = createUseCase.execute(ownerId, "Test Org").getOrThrow()
        val result = updateUseCase.execute(org.id, name = "Updated Org", callerId = ownerId)
        assertTrue(result.isSuccess)
        assertEquals("Updated Org", result.getOrThrow().name)
    }

    @Test
    fun `UpdateOrganization fails if not admin`() {
        val org = createUseCase.execute(ownerId, "Test Org").getOrThrow()
        val now = Instant.now()
        orgMembershipRepo.save(OrgMembership(UUID.randomUUID(), memberId, org.id, OrgRole.MEMBER, now, now))

        val result = updateUseCase.execute(org.id, name = "Updated Org", callerId = memberId)
        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Only org admins"))
    }

    private class InMemoryOrganizationRepository : OrganizationRepository {
        private val orgs = mutableMapOf<UUID, Organization>()
        override fun findById(id: UUID) = orgs[id]
        override fun save(organization: Organization) = organization.also { orgs[it.id] = it }
        override fun update(organization: Organization) = organization.also { orgs[it.id] = it }
        override fun delete(id: UUID) { orgs.remove(id) }
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

    private class InMemoryWorkspaceRepository : WorkspaceRepository {
        private val workspaces = mutableMapOf<UUID, Workspace>()
        override fun findById(id: UUID) = workspaces[id]
        override fun findBySlug(slug: String) = workspaces.values.find { it.slug == slug }
        override fun findByOrganizationId(organizationId: UUID) = workspaces.values.filter { it.organizationId == organizationId }
        override fun save(workspace: Workspace) = workspace.also { workspaces[it.id] = it }
        override fun delete(id: UUID) { workspaces.remove(id) }
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
