package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ConnectionStatus
import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.*
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class ReconnectSocialAccountUseCaseTest {

    private lateinit var accountRepo: ReconnectInMemorySocialAccountRepository
    private lateinit var credentialRepo: ReconnectInMemoryCredentialRepository
    private lateinit var useCase: ReconnectSocialAccountUseCase

    private val workspaceId = UUID.randomUUID()
    private val accountId = UUID.randomUUID()
    private val credentialId = UUID.randomUUID()
    private val encrypt = { token: String -> "enc_$token" }

    @BeforeEach
    fun setUp() {
        accountRepo = ReconnectInMemorySocialAccountRepository()
        credentialRepo = ReconnectInMemoryCredentialRepository()
    }

    @Test
    fun `reconnect succeeds - updates credential and sets CONNECTED`() {
        val provider = ReconnectStubProvider(PlatformType.FACEBOOK)
        val registry = ProviderRegistry.from(listOf(provider))
        useCase = ReconnectSocialAccountUseCase(accountRepo, credentialRepo, registry, encrypt)

        val cred = Credential(
            id = credentialId,
            workspaceId = workspaceId,
            platformType = PlatformType.FACEBOOK,
            encryptedAccessToken = "old_encrypted",
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        credentialRepo.save(cred)
        accountRepo.save(defaultAccount())

        val result = useCase.execute(accountId, "new_auth_code")

        assertTrue(result.isSuccess)
        val updated = result.getOrThrow()
        assertEquals(ConnectionStatus.CONNECTED, updated.connectionStatus)
        assertNull(updated.lastError)
        assertFalse(updated.analyticsNeedsReconnect)

        val updatedCred = credentialRepo.findById(credentialId)!!
        assertEquals("enc_new_access_token", updatedCred.encryptedAccessToken)
    }

    @Test
    fun `account not found - returns failure`() {
        val registry = ProviderRegistry.from(listOf(ReconnectStubProvider(PlatformType.FACEBOOK)))
        useCase = ReconnectSocialAccountUseCase(accountRepo, credentialRepo, registry, encrypt)

        val result = useCase.execute(UUID.randomUUID(), "auth_code")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Account not found"))
    }

    @Test
    fun `auth fails - returns failure`() {
        val provider = ReconnectFailingProvider(PlatformType.FACEBOOK)
        val registry = ProviderRegistry.from(listOf(provider))
        useCase = ReconnectSocialAccountUseCase(accountRepo, credentialRepo, registry, encrypt)

        accountRepo.save(defaultAccount())

        val result = useCase.execute(accountId, "bad_code")

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Re-authentication failed"))
    }

    private fun defaultAccount() = SocialAccount(
        id = accountId,
        workspaceId = workspaceId,
        credentialId = credentialId,
        platformType = PlatformType.FACEBOOK,
        platformUserId = "fb_123",
        platformUsername = "user",
        platformDisplayName = "User",
        connectionStatus = ConnectionStatus.ERROR,
        lastError = "expired",
        analyticsNeedsReconnect = true,
        connectedAt = Instant.now(),
    )
}

private class ReconnectStubProvider(
    override val platformType: PlatformType,
) : SocialProvider {

    override fun authenticate(credential: Credential): AuthResult =
        AuthResult(success = true, accessToken = "new_access_token", refreshToken = "new_refresh", expiresAt = System.currentTimeMillis() + 3600000)

    override fun refreshToken(credential: Credential): AuthResult =
        AuthResult(success = true, accessToken = "refreshed")

    override fun getProfile(socialAccount: SocialAccount): PlatformProfile =
        PlatformProfile(platformUserId = "123", platformUsername = "user", platformDisplayName = "User")

    override fun publish(post: com.brightbean.studio.domain.model.Post, socialAccount: SocialAccount) =
        PublishResult(success = true)

    override fun getComments(postId: String): List<Comment> = emptyList()

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()

    override fun getInsights(postId: String): PostInsights? = null
}

private class ReconnectFailingProvider(
    override val platformType: PlatformType,
) : SocialProvider {

    override fun authenticate(credential: Credential): AuthResult =
        AuthResult(success = false, errorMessage = "Invalid code")

    override fun refreshToken(credential: Credential): AuthResult =
        AuthResult(success = false)

    override fun getProfile(socialAccount: SocialAccount): PlatformProfile =
        PlatformProfile(platformUserId = "123", platformUsername = "user", platformDisplayName = "User")

    override fun publish(post: com.brightbean.studio.domain.model.Post, socialAccount: SocialAccount) =
        PublishResult(success = false)

    override fun getComments(postId: String): List<Comment> = emptyList()

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()

    override fun getInsights(postId: String): PostInsights? = null
}

private class ReconnectInMemorySocialAccountRepository : SocialAccountRepository {
    private val accounts = mutableMapOf<UUID, SocialAccount>()

    override fun findById(id: UUID): SocialAccount? = accounts[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<SocialAccount> =
        accounts.values.filter { it.workspaceId == workspaceId }
    override fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): List<SocialAccount> =
        accounts.values.filter { it.workspaceId == workspaceId && it.platformType == platformType }
    override fun findActiveByWorkspace(workspaceId: UUID): List<SocialAccount> =
        accounts.values.filter { it.workspaceId == workspaceId && it.isActive }
    override fun save(socialAccount: SocialAccount): SocialAccount {
        accounts[socialAccount.id] = socialAccount
        return socialAccount
    }
    override fun update(socialAccount: SocialAccount): SocialAccount {
        accounts[socialAccount.id] = socialAccount
        return socialAccount
    }
    override fun delete(id: UUID) { accounts.remove(id) }
}

private class ReconnectInMemoryCredentialRepository : CredentialRepository {
    private val credentials = mutableMapOf<UUID, Credential>()

    override fun findById(id: UUID): Credential? = credentials[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Credential> =
        credentials.values.filter { it.workspaceId == workspaceId }
    override fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): Credential? =
        credentials.values.find { it.workspaceId == workspaceId && it.platformType == platformType }
    override fun save(credential: Credential): Credential {
        credentials[credential.id] = credential
        return credential
    }
    override fun update(credential: Credential): Credential {
        credentials[credential.id] = credential
        return credential
    }
    override fun delete(id: UUID) { credentials.remove(id) }
}
