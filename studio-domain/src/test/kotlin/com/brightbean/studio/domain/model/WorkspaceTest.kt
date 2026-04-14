package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class WorkspaceTest {

    @Test
    fun `workspace settings have default values`() {
        val settings = WorkspaceSettings()
        
        assertEquals("en", settings.defaultLanguage)
        assertEquals("UTC", settings.timezone)
        assertEquals(25, settings.postsPerPage)
    }
}