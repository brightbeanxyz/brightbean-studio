package com.brightbean.studio.infrastructure.provider

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.infrastructure.provider.facebook.FacebookProvider
import com.brightbean.studio.infrastructure.provider.instagram.InstagramProvider
import com.brightbean.studio.infrastructure.provider.tiktok.TikTokProvider
import com.brightbean.studio.infrastructure.provider.linkedin.LinkedInProvider
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test

class ProviderRegistryTest {

    @Test
    fun `registry should return correct provider for platform`() {
        val registry = ProviderRegistry.from(listOf(
            FacebookProvider(),
            TikTokProvider()
        ))
        assertNotNull(registry.get(PlatformType.FACEBOOK))
        assertNotNull(registry.get(PlatformType.TIKTOK))
        assertNull(registry.get(PlatformType.INSTAGRAM))
        assertNull(registry.get(PlatformType.LINKEDIN_COMPANY))
    }

    @Test
    fun `registry should return all providers`() {
        val providers = listOf(
            FacebookProvider(),
            InstagramProvider(),
            TikTokProvider(),
            LinkedInProvider()
        )
        val registry = ProviderRegistry.from(providers)
        assertEquals(4, registry.all().size)
    }

    @Test
    fun `each provider should have correct platform type`() {
        val registry = ProviderRegistry.from(listOf(
            FacebookProvider(),
            InstagramProvider(),
            TikTokProvider(),
            LinkedInProvider()
        ))
        
        assertEquals(PlatformType.FACEBOOK, registry.get(PlatformType.FACEBOOK)?.platformType)
        assertEquals(PlatformType.INSTAGRAM, registry.get(PlatformType.INSTAGRAM)?.platformType)
        assertEquals(PlatformType.TIKTOK, registry.get(PlatformType.TIKTOK)?.platformType)
        assertEquals(PlatformType.LINKEDIN_COMPANY, registry.get(PlatformType.LINKEDIN_COMPANY)?.platformType)
    }
}
