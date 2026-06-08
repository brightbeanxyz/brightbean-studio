package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Member
import com.brightbean.studio.domain.model.MemberRole
import com.brightbean.studio.domain.model.Workspace
import com.brightbean.studio.domain.repository.MemberRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.util.UUID

class WorkspaceUseCasesTest {

    private lateinit var workspaceRepository: WorkspaceRepository
    private lateinit var memberRepository: MemberRepository
    private lateinit var createWorkspaceUseCase: CreateWorkspaceUseCase

    @BeforeEach
    fun setUp() {
        workspaceRepository = InMemoryWorkspaceRepository()
        memberRepository = InMemoryMemberRepository()
        createWorkspaceUseCase = CreateWorkspaceUseCase(workspaceRepository, memberRepository)
    }

    @Test
    fun `create workspace should create workspace with settings and owner member`() {
        val name = "Test Workspace"
        val slug = "test-workspace"
        val ownerId = UUID.randomUUID()
        val organizationId = UUID.randomUUID()

        val workspace = createWorkspaceUseCase.execute(name, slug, ownerId, organizationId)

        assertEquals(name, workspace.name)
        assertEquals(slug, workspace.slug)
        assertEquals(ownerId, workspace.ownerId)
        assertEquals("en", workspace.settings.defaultLanguage)
        assertEquals("UTC", workspace.settings.timezone)
        assertEquals(25, workspace.settings.postsPerPage)

        val members = memberRepository.findByWorkspaceId(workspace.id)
        assertEquals(1, members.size)
        assertEquals(ownerId, members[0].userId)
        assertEquals(MemberRole.OWNER, members[0].role)
    }

    @Test
    fun `create workspace should persist workspace and member`() {
        val ownerId = UUID.randomUUID()
        val organizationId = UUID.randomUUID()
        val workspace = createWorkspaceUseCase.execute("My Workspace", "my-workspace", ownerId, organizationId)

        val found = workspaceRepository.findById(workspace.id)
        assertEquals(workspace.id, found?.id)

        val members = memberRepository.findByUserId(ownerId)
        assertEquals(1, members.size)
        assertEquals(workspace.id, members[0].workspaceId)
    }
}

class InMemoryWorkspaceRepository : WorkspaceRepository {
    private val workspaces = mutableMapOf<UUID, Workspace>()

    override fun findById(id: UUID): Workspace? = workspaces[id]
    override fun findBySlug(slug: String): Workspace? = workspaces.values.find { it.slug == slug }
    override fun findByOrganizationId(organizationId: UUID): List<Workspace> = workspaces.values.filter { it.organizationId == organizationId }
    override fun save(workspace: Workspace): Workspace {
        workspaces[workspace.id] = workspace
        return workspace
    }
    override fun delete(id: UUID) { workspaces.remove(id) }
}

class InMemoryMemberRepository : MemberRepository {
    private val members = mutableMapOf<UUID, Member>()

    override fun findById(id: UUID): Member? = members[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Member> = members.values.filter { it.workspaceId == workspaceId }
    override fun findByUserId(userId: UUID): List<Member> = members.values.filter { it.userId == userId }
    override fun save(member: Member): Member {
        members[member.id] = member
        return member
    }
    override fun delete(id: UUID) { members.remove(id) }
}
