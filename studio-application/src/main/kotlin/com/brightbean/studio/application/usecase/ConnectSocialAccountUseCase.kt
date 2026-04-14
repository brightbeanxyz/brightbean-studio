package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import java.time.Instant
import java.util.UUID

class ConnectSocialAccountUseCase(
    private val socialAccountRepository: SocialAccountRepository,
    private val credentialRepository: CredentialRepository,
    private val providerRegistry: ProviderRegistry,
    private val encrypt: (String) -> String,
    private val decrypt: (String) -> String,
) {
    fun execute(
        workspaceId: UUID,
        platformType: PlatformType,
        authorizationCode: String,
    ): SocialAccount {
        val provider = providerRegistry.get(platformType)
            ?: throw IllegalArgumentException("Provider not found for platform: $platformType")

        val authResult = provider.authenticateWithCode(authorizationCode)
        if (!authResult.success || authResult.accessToken == null) {
            throw IllegalStateException("Authentication failed: ${authResult.errorMessage}")
        }

        val accessToken: String = authResult.accessToken!!
        val refreshToken: String? = authResult.refreshToken
        val expiresAt: Long? = authResult.expiresAt

        val profile = provider.getProfileFromToken(accessToken, platformType)

        val now = Instant.now()

        val existingCredential = credentialRepository.findByPlatformType(workspaceId, platformType)
        val credentialId = if (existingCredential != null) {
            val updatedCredential = existingCredential.copy(
                encryptedAccessToken = encrypt(accessToken),
                encryptedRefreshToken = refreshToken?.let { encrypt(it) },
                tokenExpiresAt = expiresAt?.let { Instant.ofEpochMilli(it) },
                updatedAt = now,
            )
            credentialRepository.update(updatedCredential)
            existingCredential.id
        } else {
            val newCredential = Credential(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                platformType = platformType,
                encryptedAccessToken = encrypt(accessToken),
                encryptedRefreshToken = refreshToken?.let { encrypt(it) },
                tokenExpiresAt = expiresAt?.let { Instant.ofEpochMilli(it) },
                createdAt = now,
                updatedAt = now,
            )
            credentialRepository.save(newCredential)
            newCredential.id
        }

        val existingAccounts = socialAccountRepository.findByPlatformType(workspaceId, platformType)
        return if (existingAccounts.isNotEmpty()) {
            val existingAccount = existingAccounts.first()
            val updatedAccount = existingAccount.copy(
                credentialId = credentialId,
                platformUserId = profile.platformUserId,
                platformUsername = profile.platformUsername,
                platformDisplayName = profile.platformDisplayName,
                platformAvatarUrl = profile.platformAvatarUrl,
                profileUrl = profile.profileUrl,
                metadata = profile.metadata,
                lastSyncAt = now,
            )
            socialAccountRepository.update(updatedAccount)
            updatedAccount
        } else {
            val newAccount = SocialAccount(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                credentialId = credentialId,
                platformType = platformType,
                platformUserId = profile.platformUserId,
                platformUsername = profile.platformUsername,
                platformDisplayName = profile.platformDisplayName,
                platformAvatarUrl = profile.platformAvatarUrl,
                profileUrl = profile.profileUrl,
                isActive = true,
                metadata = profile.metadata,
                connectedAt = now,
                lastSyncAt = now,
            )
            socialAccountRepository.save(newAccount)
            newAccount
        }
    }
}

private fun com.brightbean.studio.infrastructure.provider.SocialProvider.authenticateWithCode(code: String): com.brightbean.studio.infrastructure.provider.AuthResult {
    return this.authenticate(com.brightbean.studio.domain.model.Credential(
        id = UUID.randomUUID(),
        workspaceId = UUID.randomUUID(),
        platformType = this.platformType,
        encryptedAccessToken = code,
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    ))
}

private fun com.brightbean.studio.infrastructure.provider.SocialProvider.getProfileFromToken(token: String, platformType: PlatformType): com.brightbean.studio.infrastructure.provider.PlatformProfile {
    return this.getProfile(com.brightbean.studio.domain.model.SocialAccount(
        id = UUID.randomUUID(),
        workspaceId = UUID.randomUUID(),
        credentialId = UUID.randomUUID(),
        platformType = platformType,
        platformUserId = "",
        platformUsername = "",
        platformDisplayName = "",
        connectedAt = Instant.now(),
    ))
}