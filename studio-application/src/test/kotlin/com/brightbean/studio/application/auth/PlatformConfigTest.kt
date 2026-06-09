package com.brightbean.studio.application.auth

import com.brightbean.studio.domain.model.PlatformType
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class PlatformConfigTest {

    @Test
    fun `getCharLimit returns correct limit for each platform`() {
        assertEquals(280, PlatformConfig.getCharLimit("TWITTER"))
        assertEquals(63206, PlatformConfig.getCharLimit("FACEBOOK"))
        assertEquals(2200, PlatformConfig.getCharLimit("INSTAGRAM"))
        assertEquals(3000, PlatformConfig.getCharLimit("LINKEDIN_PERSONAL"))
    }

    @Test
    fun `getCharLimit returns default for unknown platform`() {
        assertEquals(2200, PlatformConfig.getCharLimit("UNKNOWN"))
    }

    @Test
    fun `getFieldConfig returns correct config for FACEBOOK`() {
        val config = PlatformConfig.getFieldConfig("FACEBOOK")
        assertTrue(config.supportsAltText)
        assertTrue(config.supportsFirstComment)
        assertTrue(config.supportsLink)
        assertTrue(config.supportsTagging)
        assertTrue(config.supportsLocation)
    }

    @Test
    fun `getFieldConfig returns default config for unknown platform`() {
        val config = PlatformConfig.getFieldConfig("UNKNOWN")
        assertFalse(config.supportsAltText)
        assertFalse(config.supportsFirstComment)
        assertFalse(config.supportsLink)
        assertFalse(config.supportsTagging)
        assertFalse(config.supportsLocation)
    }

    @Test
    fun `supportsFirstComment returns true for INSTAGRAM and FACEBOOK`() {
        assertTrue(PlatformConfig.supportsFirstComment("INSTAGRAM"))
        assertTrue(PlatformConfig.supportsFirstComment("FACEBOOK"))
    }

    @Test
    fun `supportsFirstComment returns false for TWITTER`() {
        assertFalse(PlatformConfig.supportsFirstComment("TWITTER"))
    }

    @Test
    fun `CHAR_LIMITS covers all PlatformType values`() {
        for (platform in PlatformType.entries) {
            assertTrue(PlatformConfig.CHAR_LIMITS.containsKey(platform.name)) {
                "Missing char limit for ${platform.name}"
            }
        }
    }
}
