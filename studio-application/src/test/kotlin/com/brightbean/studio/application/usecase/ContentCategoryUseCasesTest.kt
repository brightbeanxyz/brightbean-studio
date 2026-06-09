package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ContentCategory
import com.brightbean.studio.domain.repository.ContentCategoryRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.util.UUID

class ContentCategoryUseCasesTest {

    private lateinit var repository: ContentCategoryRepository
    private lateinit var useCases: ContentCategoryUseCases

    @BeforeEach
    fun setUp() {
        repository = CategoryInMemoryRepository()
        useCases = ContentCategoryUseCases(repository)
    }

    @Test
    fun `create category`() {
        val workspaceId = UUID.randomUUID()
        val category = useCases.create(workspaceId, "Marketing", "#FF0000")

        assertEquals("Marketing", category.name)
        assertEquals("#FF0000", category.color)
        assertEquals(0, category.position)
    }

    @Test
    fun `list categories`() {
        val workspaceId = UUID.randomUUID()
        useCases.create(workspaceId, "A", "#111111")
        useCases.create(workspaceId, "B", "#222222")

        val categories = useCases.list(workspaceId)
        assertEquals(2, categories.size)
    }

    @Test
    fun `update category`() {
        val workspaceId = UUID.randomUUID()
        val created = useCases.create(workspaceId, "Old", "#111111")

        val updated = useCases.update(created.id, "New", "#222222")

        assertEquals("New", updated.name)
        assertEquals("#222222", updated.color)
    }

    @Test
    fun `update category with partial fields`() {
        val workspaceId = UUID.randomUUID()
        val created = useCases.create(workspaceId, "Name", "#111111")

        val updated = useCases.update(created.id, null, "#222222")

        assertEquals("Name", updated.name)
        assertEquals("#222222", updated.color)
    }

    @Test
    fun `delete category`() {
        val workspaceId = UUID.randomUUID()
        val created = useCases.create(workspaceId, "Delete Me", "#111111")

        useCases.delete(created.id)

        assertTrue(useCases.list(workspaceId).isEmpty())
    }

    @Test
    fun `update non-existent category throws`() {
        assertThrows<IllegalArgumentException> {
            useCases.update(UUID.randomUUID(), "X", "#000000")
        }
    }
}

class CategoryInMemoryRepository : ContentCategoryRepository {
    private val categories = mutableMapOf<UUID, ContentCategory>()

    override fun findById(id: UUID): ContentCategory? = categories[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<ContentCategory> =
        categories.values.filter { it.workspaceId == workspaceId }.sortedBy { it.position }
    override fun save(category: ContentCategory): ContentCategory { categories[category.id] = category; return category }
    override fun update(category: ContentCategory): ContentCategory { categories[category.id] = category; return category }
    override fun delete(id: UUID) { categories.remove(id) }
}
