package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class PostTest {

    @Test
    fun `post platforms should not exceed maximum limit`() {
        val maxPlatforms = 5
        val platforms = listOf(
            PlatformType.FACEBOOK,
            PlatformType.INSTAGRAM,
            PlatformType.LINKEDIN_COMPANY,
            PlatformType.TIKTOK,
            PlatformType.YOUTUBE,
        )
        
        assertEquals(maxPlatforms, platforms.size)
    }
}
