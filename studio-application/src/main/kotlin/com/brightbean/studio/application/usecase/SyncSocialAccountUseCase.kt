package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import java.time.Instant
import java.util.UUID

class SyncSocialAccountUseCase(
    private val socialAccountRepository: SocialAccountRepository,
    private val credentialRepository: CredentialRepository,
    private val providerRegistry: ProviderRegistry,
    private val encrypt: (String) -> String,
    private val decrypt: (String) -> String,
) {
    fun execute(socialAccountId: UUID): SocialAccount {
        val socialAccount = socialAccountRepository.findById(socialAccountId)
            ?: throw IllegalArgumentException("Social account not found: $socialAccountId")

        val provider = providerRegistry.get(socialAccount.platformType)
            ?: throw IllegalArgumentException("Provider not found for platform: ${socialAccount.platformType}")

        val credential = credentialRepository.findById(socialAccount.credentialId)
            ?: throw IllegalStateException("Credential not found for social account: $socialAccountId")

        val decryptedAccessToken = decrypt(credential.encryptedAccessToken)
        val decryptedRefreshToken = credential.encryptedRefreshToken?.let { decrypt(it) }

        val decryptedCredential = Credential(
            id = credential.id,
            workspaceId = credential.workspaceId,
            platformType = credential.platformType,
            encryptedAccessToken = decryptedAccessToken,
            encryptedRefreshToken = decryptedRefreshToken,
            tokenExpiresAt = credential.tokenExpiresAt,
            metadata = credential.metadata,
            createdAt = credential.createdAt,
            updatedAt = credential.updatedAt,
        )

        val refreshedAuthResult = provider.refreshToken(decryptedCredential)
        if (refreshedAuthResult.success && refreshedAuthResult.accessToken != null) {
            val newAccessToken: String = refreshedAuthResult.accessToken!!
            val newRefreshToken: String? = refreshedAuthResult.refreshToken
            val newExpiresAt: Long? = refreshedAuthResult.expiresAt

            val updatedCredential = decryptedCredential.copy(
                encryptedAccessToken = encrypt(newAccessToken),
                encryptedRefreshToken = newRefreshToken?.let { encrypt(it) },
                tokenExpiresAt = newExpiresAt?.let { Instant.ofEpochMilli(it) },
                updatedAt = Instant.now(),
            )
            credentialRepository.update(updatedCredential)
        }

        val profile = provider.getProfile(socialAccount)

        val now = Instant.now()
        val updatedAccount = socialAccount.copy(
            platformUserId = profile.platformUserId,
            platformUsername = profile.platformUsername,
            platformDisplayName = profile.platformDisplayName,
            platformAvatarUrl = profile.platformAvatarUrl,
            profileUrl = profile.profileUrl,
            metadata = profile.metadata,
            lastSyncAt = now,
        )

        return socialAccountRepository.update(updatedAccount)
    }
}