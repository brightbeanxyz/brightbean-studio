package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.OrgSetting
import com.brightbean.studio.domain.model.WorkspaceSetting
import com.brightbean.studio.domain.repository.OrgSettingRepository
import com.brightbean.studio.domain.repository.WorkspaceSettingRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class SettingsUseCasesTest {

    private lateinit var orgSettingRepo: InMemOrgSettingRepo
    private lateinit var workspaceSettingRepo: InMemWorkspaceSettingRepo
    private lateinit var useCases: SettingsUseCases

    @BeforeEach
    fun setUp() {
        orgSettingRepo = InMemOrgSettingRepo()
        workspaceSettingRepo = InMemWorkspaceSettingRepo()
        useCases = SettingsUseCases(orgSettingRepo, workspaceSettingRepo)
    }

    @Test
    fun `setOrgSetting creates new setting`() {
        val orgId = UUID.randomUUID()
        val setting = useCases.setOrgSetting(orgId, "timezone", "US/Eastern")

        assertEquals("timezone", setting.key)
        assertEquals("US/Eastern", setting.value)
        assertEquals(1, useCases.getOrgSettings(orgId).size)
    }

    @Test
    fun `setOrgSetting updates existing setting`() {
        val orgId = UUID.randomUUID()
        useCases.setOrgSetting(orgId, "timezone", "UTC")
        val updated = useCases.setOrgSetting(orgId, "timezone", "US/Eastern")

        assertEquals("US/Eastern", updated.value)
        assertEquals(1, useCases.getOrgSettings(orgId).size)
    }

    @Test
    fun `getOrgSetting returns specific setting`() {
        val orgId = UUID.randomUUID()
        useCases.setOrgSetting(orgId, "timezone", "UTC")
        useCases.setOrgSetting(orgId, "language", "en")

        val found = useCases.getOrgSetting(orgId, "timezone")
        assertNotNull(found)
        assertEquals("UTC", found!!.value)
    }

    @Test
    fun `getOrgSetting returns null for missing key`() {
        assertNull(useCases.getOrgSetting(UUID.randomUUID(), "missing"))
    }

    @Test
    fun `setWorkspaceSetting creates new setting`() {
        val wsId = UUID.randomUUID()
        val setting = useCases.setWorkspaceSetting(wsId, "posts_per_page", "50")

        assertEquals("posts_per_page", setting.key)
        assertEquals("50", setting.value)
    }

    @Test
    fun `setWorkspaceSetting updates existing setting`() {
        val wsId = UUID.randomUUID()
        useCases.setWorkspaceSetting(wsId, "posts_per_page", "25")
        val updated = useCases.setWorkspaceSetting(wsId, "posts_per_page", "50")

        assertEquals("50", updated.value)
        assertEquals(1, useCases.getWorkspaceSettings(wsId).size)
    }

    @Test
    fun `getWorkspaceSetting returns specific setting`() {
        val wsId = UUID.randomUUID()
        useCases.setWorkspaceSetting(wsId, "theme", "dark")

        val found = useCases.getWorkspaceSetting(wsId, "theme")
        assertNotNull(found)
        assertEquals("dark", found!!.value)
    }

    class InMemOrgSettingRepo : OrgSettingRepository {
        private val items = mutableMapOf<Pair<UUID, String>, OrgSetting>()
        override fun findByOrganizationId(organizationId: UUID) = items.values.filter { it.organizationId == organizationId }
        override fun findByKey(organizationId: UUID, key: String) = items[Pair(organizationId, key)]
        override fun save(s: OrgSetting) = s.also { items[Pair(s.organizationId, s.key)] = it }
        override fun update(s: OrgSetting) = s.also { items[Pair(s.organizationId, s.key)] = it }
    }

    class InMemWorkspaceSettingRepo : WorkspaceSettingRepository {
        private val items = mutableMapOf<Pair<UUID, String>, WorkspaceSetting>()
        override fun findByWorkspaceId(workspaceId: UUID) = items.values.filter { it.workspaceId == workspaceId }
        override fun findByKey(workspaceId: UUID, key: String) = items[Pair(workspaceId, key)]
        override fun save(s: WorkspaceSetting) = s.also { items[Pair(s.workspaceId, s.key)] = it }
        override fun update(s: WorkspaceSetting) = s.also { items[Pair(s.workspaceId, s.key)] = it }
    }
}
