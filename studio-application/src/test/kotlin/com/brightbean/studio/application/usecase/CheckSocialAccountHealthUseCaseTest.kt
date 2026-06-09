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

class CheckSocialAccountHealthUseCaseTest {

    private lateinit var accountRepo: HealthInMemorySocialAccountRepository
    private lateinit var credentialRepo: HealthInMemoryCredentialRepository
    private lateinit var useCase: CheckSocialAccountHealthUseCase

    private val workspaceId = UUID.randomUUID()
    private val accountId = UUID.randomUUID()
    private val credentialId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        accountRepo = HealthInMemorySocialAccountRepository()
        credentialRepo = HealthInMemoryCredentialRepository()
    }

    @Test
    fun `health check succeeds - sets CONNECTED and updates profile data`() {
        val provider = HealthStubProvider(PlatformType.FACEBOOK)
        val registry = ProviderRegistry.from(listOf(provider))
        useCase = CheckSocialAccountHealthUseCase(accountRepo, credentialRepo, registry)

        accountRepo.save(defaultAccount())
        val result = useCase.execute(accountId)

        assertTrue(result.isSuccess)
        val updated = result.getOrThrow()
        assertEquals(ConnectionStatus.CONNECTED, updated.connectionStatus)
        assertNull(updated.lastError)
        assertNotNull(updated.lastHealthCheckAt)
        assertNotNull(updated.lastSyncAt)
        assertEquals("test_user", updated.platformUsername)
        assertEquals("Test User", updated.platformDisplayName)
    }

    @Test
    fun `health check fails with token error - sets ERROR with friendly message`() {
        val provider = HealthStubProvider(PlatformType.FACEBOOK, shouldThrow = RuntimeException("token expired"))
        val registry = ProviderRegistry.from(listOf(provider))
        useCase = CheckSocialAccountHealthUseCase(accountRepo, credentialRepo, registry)

        accountRepo.save(defaultAccount())
        val result = useCase.execute(accountId)

        assertTrue(result.isSuccess)
        val updated = result.getOrThrow()
        assertEquals(ConnectionStatus.ERROR, updated.connectionStatus)
        assertTrue(updated.lastError!!.contains("expired"))
    }

    @Test
    fun `health check fails with rate limit - sets ERROR with rate limit message`() {
        val provider = HealthStubProvider(PlatformType.FACEBOOK, shouldThrow = RuntimeException("rate limit exceeded"))
        val registry = ProviderRegistry.from(listOf(provider))
        useCase = CheckSocialAccountHealthUseCase(accountRepo, credentialRepo, registry)

        accountRepo.save(defaultAccount())
        val result = useCase.execute(accountId)

        assertTrue(result.isSuccess)
        val updated = result.getOrThrow()
        assertEquals(ConnectionStatus.ERROR, updated.connectionStatus)
        assertTrue(updated.lastError!!.contains("Rate limit"))
    }

    @Test
    fun `account not found - returns failure`() {
        useCase = CheckSocialAccountHealthUseCase(accountRepo, credentialRepo, ProviderRegistry.from(emptyList()))

        val result = useCase.execute(UUID.randomUUID())

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()!!.message!!.contains("Account not found"))
    }

    @Test
    fun `no provider - sets ERROR with no provider configured`() {
        val registry = ProviderRegistry.from(emptyList())
        useCase = CheckSocialAccountHealthUseCase(accountRepo, credentialRepo, registry)

        accountRepo.save(defaultAccount())
        val result = useCase.execute(accountId)

        assertTrue(result.isSuccess)
        val updated = result.getOrThrow()
        assertEquals(ConnectionStatus.ERROR, updated.connectionStatus)
        assertTrue(updated.lastError!!.contains("No provider configured"))
    }

    private fun defaultAccount() = SocialAccount(
        id = accountId,
        workspaceId = workspaceId,
        credentialId = credentialId,
        platformType = PlatformType.FACEBOOK,
        platformUserId = "fb_123",
        platformUsername = "old_user",
        platformDisplayName = "Old Name",
        connectedAt = Instant.now(),
    )
}

private class HealthStubProvider(
    override val platformType: PlatformType,
    private val shouldThrow: Exception? = null,
) : SocialProvider {

    override fun authenticate(credential: Credential): AuthResult =
        AuthResult(success = true, accessToken = "token")

    override fun getProfile(socialAccount: SocialAccount): PlatformProfile {
        shouldThrow?.let { throw it }
        return PlatformProfile(
            platformUserId = "123",
            platformUsername = "test_user",
            platformDisplayName = "Test User",
            platformAvatarUrl = "https://avatar.url",
            profileUrl = "https://profile.url",
        )
    }

    override fun publishPost(account: SocialAccount, content: com.brightbean.studio.infrastructure.provider.types.PublishContent) =
        PublishResult(success = true)

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()
}

private class HealthInMemorySocialAccountRepository : SocialAccountRepository {
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

private class HealthInMemoryCredentialRepository : CredentialRepository {
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
