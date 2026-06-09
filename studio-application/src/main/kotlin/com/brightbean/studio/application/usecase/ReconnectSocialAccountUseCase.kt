package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ConnectionStatus
import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import java.time.Instant
import java.util.UUID

class ReconnectSocialAccountUseCase(
    private val socialAccountRepository: SocialAccountRepository,
    private val credentialRepository: CredentialRepository,
    private val providerRegistry: ProviderRegistry,
    private val encrypt: (String) -> String,
) {
    fun execute(accountId: UUID, authorizationCode: String): Result<SocialAccount> {
        val account = socialAccountRepository.findById(accountId)
            ?: return Result.failure(IllegalArgumentException("Account not found"))

        val provider = providerRegistry.get(account.platformType)
            ?: return Result.failure(IllegalArgumentException("Provider not found for platform: ${account.platformType}"))

        val authResult = provider.authenticate(Credential(
            id = UUID.randomUUID(),
            workspaceId = account.workspaceId,
            platformType = account.platformType,
            encryptedAccessToken = authorizationCode,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        ))
        if (!authResult.success || authResult.accessToken == null) {
            return Result.failure(IllegalStateException("Re-authentication failed: ${authResult.errorMessage}"))
        }

        val accessToken: String = authResult.accessToken!!
        val refreshToken: String? = authResult.refreshToken
        val expiresAt: Long? = authResult.expiresAt

        val now = Instant.now()
        val existingCred = credentialRepository.findById(account.credentialId)
        if (existingCred != null) {
            credentialRepository.update(existingCred.copy(
                encryptedAccessToken = encrypt(accessToken),
                encryptedRefreshToken = refreshToken?.let { encrypt(it) },
                tokenExpiresAt = expiresAt?.let { Instant.ofEpochMilli(it) },
                updatedAt = now,
            ))
        }

        val updated = account.copy(
            connectionStatus = ConnectionStatus.CONNECTED,
            lastError = null,
            analyticsNeedsReconnect = false,
            lastSyncAt = now,
        )
        return Result.success(socialAccountRepository.update(updated))
    }
}
