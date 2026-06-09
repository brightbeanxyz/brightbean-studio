package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ConnectionStatus
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import java.time.Instant
import java.util.UUID

class CheckSocialAccountHealthUseCase(
    private val socialAccountRepository: SocialAccountRepository,
    private val credentialRepository: CredentialRepository,
    private val providerRegistry: ProviderRegistry,
) {
    fun execute(accountId: UUID): Result<SocialAccount> {
        val account = socialAccountRepository.findById(accountId)
            ?: return Result.failure(IllegalArgumentException("Account not found"))

        val provider = providerRegistry.get(account.platformType)
        val now = Instant.now()

        if (provider == null) {
            val updated = account.copy(
                connectionStatus = ConnectionStatus.ERROR,
                lastHealthCheckAt = now,
                lastError = "No provider configured for platform: ${account.platformType}",
            )
            return Result.success(socialAccountRepository.update(updated))
        }

        return try {
            val profile = provider.getProfile(account)
            val updated = account.copy(
                connectionStatus = ConnectionStatus.CONNECTED,
                lastHealthCheckAt = now,
                lastError = null,
                platformDisplayName = profile.platformDisplayName,
                platformUsername = profile.platformUsername,
                platformAvatarUrl = profile.platformAvatarUrl,
                lastSyncAt = now,
            )
            Result.success(socialAccountRepository.update(updated))
        } catch (e: Exception) {
            val errorMessage = friendlyHealthCheckError(e)
            val updated = account.copy(
                connectionStatus = ConnectionStatus.ERROR,
                lastHealthCheckAt = now,
                lastError = errorMessage,
            )
            Result.success(socialAccountRepository.update(updated))
        }
    }

    private fun friendlyHealthCheckError(e: Exception): String {
        val msg = e.message?.lowercase() ?: ""
        return when {
            "token" in msg || "401" in msg || "403" in msg -> "Account connection expired. Please reconnect."
            "rate limit" in msg || "429" in msg -> "Rate limit reached. We'll retry this check shortly."
            "500" in msg || "502" in msg || "503" in msg || "504" in msg -> "Platform temporarily unavailable. We'll retry this check shortly."
            else -> "Connection check failed. Please try reconnecting."
        }
    }
}
