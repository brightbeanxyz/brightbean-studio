package com.brightbean.studio.infrastructure.provider

import com.brightbean.studio.domain.model.PlatformType

class ProviderRegistry(
    private val providers: Map<PlatformType, SocialProvider>
) {
    fun get(platformType: PlatformType): SocialProvider? = providers[platformType]

    fun all(): Collection<SocialProvider> = providers.values

    companion object {
        fun from(providers: List<SocialProvider>) = ProviderRegistry(
            providers.associateBy { it.platformType }
        )
    }
}
