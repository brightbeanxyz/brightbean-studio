package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.AuthResult
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.SocialProvider
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class ConnectSocialAccountUseCaseTest {

    private lateinit var socialAccountRepository: SocialAccountRepository
    private lateinit var credentialRepository: CredentialRepository
    private lateinit var providerRegistry: ProviderRegistry
    private lateinit var connectUseCase: ConnectSocialAccountUseCase

    private val workspaceId = UUID.randomUUID()
    private val encryptToken = { token: String -> "encrypted_$token" }
    private val decryptToken = { encrypted: String -> encrypted.removePrefix("encrypted_") }

    @BeforeEach
    fun setUp() {
        socialAccountRepository = ConnectInMemorySocialAccountRepository()
        credentialRepository = ConnectInMemoryCredentialRepository()
        providerRegistry = ProviderRegistry.from(listOf(ConnectFakeFacebookProvider()))
        connectUseCase = ConnectSocialAccountUseCase(
            socialAccountRepository,
            credentialRepository,
            providerRegistry,
            encryptToken,
            decryptToken,
        )
    }

    @Test
    fun `execute should create new social account when none exists`() {
        val result = connectUseCase.execute(workspaceId, PlatformType.FACEBOOK, "auth_code_123")

        assertNotNull(result)
        assertEquals(workspaceId, result.workspaceId)
        assertEquals(PlatformType.FACEBOOK, result.platformType)
        assertEquals("fb_user_456", result.platformUserId)
        assertEquals("testuser", result.platformUsername)
        assertEquals("Test User", result.platformDisplayName)
        assertEquals(true, result.isActive)
    }

    @Test
    fun `execute should create credential along with social account`() {
        val result = connectUseCase.execute(workspaceId, PlatformType.FACEBOOK, "auth_code_123")

        val credentials = credentialRepository.findByWorkspaceId(workspaceId)
        assertEquals(1, credentials.size)
        assertEquals(PlatformType.FACEBOOK, credentials.first().platformType)
        assertEquals("encrypted_test_access_token", credentials.first().encryptedAccessToken)
    }

    @Test
    fun `execute should update existing credential when connecting again`() {
        connectUseCase.execute(workspaceId, PlatformType.FACEBOOK, "auth_code_123")
        val credentialsBefore = credentialRepository.findByWorkspaceId(workspaceId)

        connectUseCase.execute(workspaceId, PlatformType.FACEBOOK, "new_auth_code")

        val credentialsAfter = credentialRepository.findByWorkspaceId(workspaceId)
        assertEquals(1, credentialsAfter.size)
        assertEquals(credentialsBefore.first().id, credentialsAfter.first().id)
    }

    @Test
    fun `execute should update existing social account when reconnecting`() {
        connectUseCase.execute(workspaceId, PlatformType.FACEBOOK, "auth_code_123")
        val accountsBefore = socialAccountRepository.findByPlatformType(workspaceId, PlatformType.FACEBOOK)

        connectUseCase.execute(workspaceId, PlatformType.FACEBOOK, "new_auth_code")

        val accountsAfter = socialAccountRepository.findByPlatformType(workspaceId, PlatformType.FACEBOOK)
        assertEquals(1, accountsAfter.size)
    }

    @Test
    fun `execute should throw when provider not found`() {
        assertThrows(IllegalArgumentException::class.java) {
            connectUseCase.execute(workspaceId, PlatformType.TIKTOK, "auth_code")
        }
    }

    @Test
    fun `execute should throw when authentication fails`() {
        val failingProviderRegistry = ProviderRegistry.from(listOf(ConnectFailingProvider()))
        val failingUseCase = ConnectSocialAccountUseCase(
            socialAccountRepository,
            credentialRepository,
            failingProviderRegistry,
            encryptToken,
            decryptToken,
        )

        assertThrows(IllegalStateException::class.java) {
            failingUseCase.execute(workspaceId, PlatformType.FACEBOOK, "bad_code")
        }
    }
}

class ConnectFakeFacebookProvider : SocialProvider {
    override val platformType = PlatformType.FACEBOOK

    override fun authenticate(credential: Credential): AuthResult {
        return AuthResult(
            success = true,
            accessToken = "test_access_token",
            refreshToken = "test_refresh_token",
            expiresAt = System.currentTimeMillis() + 3600000,
        )
    }

    override fun refreshToken(credential: Credential): AuthResult {
        return AuthResult(success = true, accessToken = "refreshed_token")
    }

    override fun getProfile(socialAccount: SocialAccount): PlatformProfile {
        return PlatformProfile(
            platformUserId = "fb_user_456",
            platformUsername = "testuser",
            platformDisplayName = "Test User",
            platformAvatarUrl = null,
            profileUrl = null,
        )
    }

    override fun publish(post: com.brightbean.studio.domain.model.Post, socialAccount: SocialAccount) =
        com.brightbean.studio.infrastructure.provider.PublishResult(success = true, platformPostId = "post_123")

    override fun getComments(postId: String): List<com.brightbean.studio.infrastructure.provider.Comment> = emptyList()

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()

    override fun getInsights(postId: String): com.brightbean.studio.infrastructure.provider.PostInsights? = null
}

class ConnectFailingProvider : SocialProvider {
    override val platformType = PlatformType.FACEBOOK

    override fun authenticate(credential: Credential): AuthResult {
        return AuthResult(success = false, errorMessage = "Invalid authorization code")
    }

    override fun refreshToken(credential: Credential): AuthResult {
        return AuthResult(success = false)
    }

    override fun getProfile(socialAccount: SocialAccount): PlatformProfile {
        return PlatformProfile(
            platformUserId = "user",
            platformUsername = "user",
            platformDisplayName = "User",
        )
    }

    override fun publish(post: com.brightbean.studio.domain.model.Post, socialAccount: SocialAccount) =
        com.brightbean.studio.infrastructure.provider.PublishResult(success = false)

    override fun getComments(postId: String): List<com.brightbean.studio.infrastructure.provider.Comment> = emptyList()

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()

    override fun getInsights(postId: String): com.brightbean.studio.infrastructure.provider.PostInsights? = null
}

class ConnectInMemorySocialAccountRepository : SocialAccountRepository {
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

class ConnectInMemoryCredentialRepository : CredentialRepository {
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