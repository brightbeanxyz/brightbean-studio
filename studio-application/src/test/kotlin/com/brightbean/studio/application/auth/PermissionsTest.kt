package com.brightbean.studio.application.auth

import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.WorkspaceRole
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test

class PermissionsTest {

    @Test
    fun `OWNER has all workspace permissions`() {
        val ownerPerms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.OWNER]!!
        WorkspacePermissionKeys.ALL.forEach { key ->
            assertTrue(ownerPerms.contains(key), "OWNER should have $key")
        }
    }

    @Test
    fun `VIEWER has only view_analytics`() {
        val viewerPerms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.VIEWER]!!
        assertEquals(setOf(WorkspacePermissionKeys.VIEW_ANALYTICS), viewerPerms)
    }

    @Test
    fun `EDITOR does not have manage_workspace_settings`() {
        val editorPerms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.EDITOR]!!
        assertFalse(editorPerms.contains(WorkspacePermissionKeys.MANAGE_WORKSPACE_SETTINGS))
    }

    @Test
    fun `MANAGER does not have manage_workspace_settings`() {
        val managerPerms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.MANAGER]!!
        assertFalse(managerPerms.contains(WorkspacePermissionKeys.MANAGE_WORKSPACE_SETTINGS))
    }

    @Test
    fun `MANAGER has all other permissions`() {
        val managerPerms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.MANAGER]!!
        val expected = WorkspacePermissionKeys.ALL.toSet() - WorkspacePermissionKeys.MANAGE_WORKSPACE_SETTINGS
        assertEquals(expected, managerPerms)
    }

    @Test
    fun `CONTRIBUTOR has create_posts and view_analytics`() {
        val perms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.CONTRIBUTOR]!!
        assertTrue(perms.contains(WorkspacePermissionKeys.CREATE_POSTS))
        assertTrue(perms.contains(WorkspacePermissionKeys.VIEW_ANALYTICS))
        assertFalse(perms.contains(WorkspacePermissionKeys.PUBLISH_DIRECTLY))
    }

    @Test
    fun `CLIENT has approve_posts and view_analytics`() {
        val perms = BUILTIN_WORKSPACE_PERMISSIONS[WorkspaceRole.CLIENT]!!
        assertEquals(setOf(WorkspacePermissionKeys.APPROVE_POSTS, WorkspacePermissionKeys.VIEW_ANALYTICS), perms)
    }

    @Test
    fun `workspace role levels are ordered correctly`() {
        assertTrue(WORKSPACE_ROLE_LEVEL[WorkspaceRole.OWNER]!! > WORKSPACE_ROLE_LEVEL[WorkspaceRole.MANAGER]!!)
        assertTrue(WORKSPACE_ROLE_LEVEL[WorkspaceRole.MANAGER]!! > WORKSPACE_ROLE_LEVEL[WorkspaceRole.EDITOR]!!)
        assertTrue(WORKSPACE_ROLE_LEVEL[WorkspaceRole.EDITOR]!! > WORKSPACE_ROLE_LEVEL[WorkspaceRole.CONTRIBUTOR]!!)
        assertTrue(WORKSPACE_ROLE_LEVEL[WorkspaceRole.CONTRIBUTOR]!! > WORKSPACE_ROLE_LEVEL[WorkspaceRole.CLIENT]!!)
        assertTrue(WORKSPACE_ROLE_LEVEL[WorkspaceRole.CLIENT]!! > WORKSPACE_ROLE_LEVEL[WorkspaceRole.VIEWER]!!)
    }

    @Test
    fun `org role levels are ordered correctly`() {
        assertTrue(ORG_ROLE_LEVEL[OrgRole.OWNER]!! > ORG_ROLE_LEVEL[OrgRole.ADMIN]!!)
        assertTrue(ORG_ROLE_LEVEL[OrgRole.ADMIN]!! > ORG_ROLE_LEVEL[OrgRole.MEMBER]!!)
    }

    @Test
    fun `OWNER org role has all org permissions`() {
        val ownerPerms = BUILTIN_ORG_PERMISSIONS[OrgRole.OWNER]!!
        OrgPermissionKeys.ALL.forEach { key ->
            assertTrue(ownerPerms.contains(key), "OWNER should have $key")
        }
    }

    @Test
    fun `MEMBER org role has only use_intelligence`() {
        val memberPerms = BUILTIN_ORG_PERMISSIONS[OrgRole.MEMBER]!!
        assertEquals(setOf(OrgPermissionKeys.USE_INTELLIGENCE), memberPerms)
    }

    @Test
    fun `ALL workspace permission keys list is complete`() {
        assertEquals(13, WorkspacePermissionKeys.ALL.size)
        assertEquals(WorkspacePermissionKeys.ALL.toSet().size, WorkspacePermissionKeys.ALL.size)
    }

    @Test
    fun `ALL org permission keys list is complete`() {
        assertEquals(3, OrgPermissionKeys.ALL.size)
    }
}
