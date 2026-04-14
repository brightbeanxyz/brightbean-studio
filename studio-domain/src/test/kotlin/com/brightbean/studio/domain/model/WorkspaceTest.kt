package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Test
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue

class WorkspaceTest {

    @Test
    fun `workspace settings have default values`() {
        val settings = WorkspaceSettings()
        
        assertTrue(settings.isPublic)
        assertFalse(settings.allowMemberInvite)
        assertFalse(settings.allowBoardCreation)
        assertFalse(settings.allowCardCreation)
    }
}