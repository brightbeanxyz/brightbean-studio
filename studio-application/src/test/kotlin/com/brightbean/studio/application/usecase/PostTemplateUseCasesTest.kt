package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PostTemplate
import com.brightbean.studio.domain.repository.PostTemplateRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.util.UUID

class PostTemplateUseCasesTest {

    private lateinit var repository: PostTemplateInMemoryRepository
    private lateinit var useCases: PostTemplateUseCases

    @BeforeEach
    fun setUp() {
        repository = PostTemplateInMemoryRepository()
        useCases = PostTemplateUseCases(repository)
    }

    @Test
    fun `save as template`() {
        val workspaceId = UUID.randomUUID()
        val template = useCases.saveAsTemplate(workspaceId, "Newsletter", "Monthly newsletter", """{"caption":"Hello"}""", null)

        assertEquals("Newsletter", template.name)
        assertEquals("Monthly newsletter", template.description)
        assertEquals("""{"caption":"Hello"}""", template.templateData)
        assertEquals(workspaceId, template.workspaceId)
    }

    @Test
    fun `list templates`() {
        val workspaceId = UUID.randomUUID()
        useCases.saveAsTemplate(workspaceId, "T1", "", "{}", null)
        useCases.saveAsTemplate(workspaceId, "T2", "", "{}", null)

        val templates = useCases.list(workspaceId)
        assertEquals(2, templates.size)
    }
}

class PostTemplateInMemoryRepository : PostTemplateRepository {
    private val items = mutableMapOf<UUID, PostTemplate>()

    override fun findById(id: UUID): PostTemplate? = items[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<PostTemplate> =
        items.values.filter { it.workspaceId == workspaceId }
    override fun save(template: PostTemplate): PostTemplate { items[template.id] = template; return template }
    override fun update(template: PostTemplate): PostTemplate { items[template.id] = template; return template }
    override fun delete(id: UUID) { items.remove(id) }
}
