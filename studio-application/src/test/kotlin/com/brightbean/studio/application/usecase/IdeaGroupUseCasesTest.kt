package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.IdeaGroup
import com.brightbean.studio.domain.repository.IdeaGroupRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.util.UUID

class IdeaGroupUseCasesTest {

    private lateinit var repository: IdeaGroupRepository
    private lateinit var useCases: IdeaGroupUseCases

    @BeforeEach
    fun setUp() {
        repository = GroupInMemoryRepository()
        useCases = IdeaGroupUseCases(repository)
    }

    @Test
    fun `create group`() {
        val workspaceId = UUID.randomUUID()
        val group = useCases.create(workspaceId, "Kanban Column")

        assertEquals("Kanban Column", group.name)
        assertEquals(0, group.position)
    }

    @Test
    fun `list groups`() {
        val workspaceId = UUID.randomUUID()
        useCases.create(workspaceId, "A")
        useCases.create(workspaceId, "B")

        val groups = useCases.list(workspaceId)
        assertEquals(2, groups.size)
    }

    @Test
    fun `delete group`() {
        val workspaceId = UUID.randomUUID()
        val group = useCases.create(workspaceId, "Delete Me")

        useCases.delete(group.id)

        assertTrue(useCases.list(workspaceId).isEmpty())
    }

    @Test
    fun `reorder groups`() {
        val workspaceId = UUID.randomUUID()
        val g1 = useCases.create(workspaceId, "A")
        val g2 = useCases.create(workspaceId, "B")
        val g3 = useCases.create(workspaceId, "C")

        useCases.reorder(listOf(g3.id, g1.id, g2.id))

        val groups = useCases.list(workspaceId).sortedBy { it.position }
        assertEquals(g3.id, groups[0].id)
        assertEquals(0, groups[0].position)
        assertEquals(g1.id, groups[1].id)
        assertEquals(1, groups[1].position)
        assertEquals(g2.id, groups[2].id)
        assertEquals(2, groups[2].position)
    }
}

class GroupInMemoryRepository : IdeaGroupRepository {
    private val groups = mutableMapOf<UUID, IdeaGroup>()

    override fun findById(id: UUID): IdeaGroup? = groups[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<IdeaGroup> =
        groups.values.filter { it.workspaceId == workspaceId }.sortedBy { it.position }
    override fun save(group: IdeaGroup): IdeaGroup { groups[group.id] = group; return group }
    override fun update(group: IdeaGroup): IdeaGroup { groups[group.id] = group; return group }
    override fun delete(id: UUID) { groups.remove(id) }
}
