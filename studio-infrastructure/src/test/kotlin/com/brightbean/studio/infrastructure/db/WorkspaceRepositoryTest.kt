package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Workspace
import com.brightbean.studio.domain.model.WorkspaceSettings
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID
import org.junit.jupiter.api.Assertions.*

class WorkspaceRepositoryTest {

    private lateinit var jdbi: Jdbi
    private lateinit var repository: JDBIWorkspaceRepository

    @BeforeEach
    fun setUp() {
        jdbi = Jdbi.create("jdbc:h2:mem:test_${UUID.randomUUID()};DB_CLOSE_DELAY=-1")
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())

        jdbi.useHandle<Exception> { handle ->
            handle.createUpdate("""
                CREATE TABLE workspace (
                    id UUID PRIMARY KEY,
                    organization_id UUID NOT NULL,
                    name VARCHAR NOT NULL,
                    slug VARCHAR NOT NULL UNIQUE,
                    owner_id UUID NOT NULL,
                    settings TEXT NOT NULL,
                    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """).execute()
        }

        repository = JDBIWorkspaceRepository(jdbi)
    }

    @Test
    fun `findById returns workspace when exists`() {
        val workspace = createTestWorkspace()
        repository.save(workspace)

        val found = repository.findById(workspace.id)

        assertNotNull(found)
        assertEquals(workspace.id, found!!.id)
        assertEquals(workspace.name, found.name)
        assertEquals(workspace.slug, found.slug)
    }

    @Test
    fun `findById returns null when not exists`() {
        val found = repository.findById(UUID.randomUUID())
        assertNull(found)
    }

    @Test
    fun `findBySlug returns workspace when exists`() {
        val workspace = createTestWorkspace()
        repository.save(workspace)

        val found = repository.findBySlug(workspace.slug)

        assertNotNull(found)
        assertEquals(workspace.id, found!!.id)
        assertEquals(workspace.slug, found.slug)
    }

    @Test
    fun `findBySlug returns null when not exists`() {
        val found = repository.findBySlug("nonexistent-slug")
        assertNull(found)
    }

    @Test
    fun `save inserts and returns workspace`() {
        val workspace = createTestWorkspace()

        val saved = repository.save(workspace)

        assertNotNull(saved)
        assertEquals(workspace.id, saved.id)
        assertEquals(workspace.name, saved.name)
    }

    @Test
    fun `delete removes workspace`() {
        val workspace = createTestWorkspace()
        repository.save(workspace)

        repository.delete(workspace.id)

        val found = repository.findById(workspace.id)
        assertNull(found)
    }

    private fun createTestWorkspace(): Workspace {
        return Workspace(
            id = UUID.randomUUID(),
            organizationId = UUID.randomUUID(),
            name = "Test Workspace",
            slug = "test-workspace-${UUID.randomUUID()}",
            ownerId = UUID.randomUUID(),
            settings = WorkspaceSettings(
                defaultLanguage = "en",
                timezone = "UTC",
                postsPerPage = 25
            ),
            createdAt = Instant.now(),
            updatedAt = Instant.now()
        )
    }
}
