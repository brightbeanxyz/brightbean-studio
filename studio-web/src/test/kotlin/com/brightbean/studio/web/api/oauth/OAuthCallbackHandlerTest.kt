package com.brightbean.studio.web.api.oauth

import com.brightbean.studio.application.usecase.ConnectSocialAccountUseCase
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.SocialAccountRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.mockito.Mockito
import java.util.UUID

class OAuthCallbackHandlerTest {

    private lateinit var socialAccountRepository: SocialAccountRepository
    private lateinit var connectSocialAccountUseCase: ConnectSocialAccountUseCase
    private lateinit var facebookHandler: FacebookOAuthHandler
    private lateinit var googleHandler: GoogleOAuthHandler

    private val workspaceId = UUID.randomUUID()
    private val encryptToken = { token: String -> "encrypted_$token" }
    private val decryptToken = { encrypted: String -> encrypted.removePrefix("encrypted_") }

    @BeforeEach
    fun setUp() {
        socialAccountRepository = Mockito.mock(SocialAccountRepository::class.java)
        connectSocialAccountUseCase = Mockito.mock(ConnectSocialAccountUseCase::class.java)
        facebookHandler = FacebookOAuthHandler(connectSocialAccountUseCase, socialAccountRepository)
        googleHandler = GoogleOAuthHandler(connectSocialAccountUseCase, socialAccountRepository)
    }

    @Test
    fun `FacebookOAuthHandler returns OAuthResult with correct platform type`() {
        val code = "auth_code_123"
        val state = workspaceId.toString()
        val redirectUri = "https://example.com/oauth/facebook"

        val socialAccount = SocialAccount(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            credentialId = UUID.randomUUID(),
            platformType = PlatformType.FACEBOOK,
            platformUserId = "fb_user_456",
            platformUsername = "testuser",
            platformDisplayName = "Test User",
            platformAvatarUrl = null,
            profileUrl = null,
            isActive = true,
            metadata = emptyMap(),
            connectedAt = java.time.Instant.now(),
            lastSyncAt = java.time.Instant.now(),
        )

        Mockito.doReturn(socialAccount).`when`(connectSocialAccountUseCase).execute(
            workspaceId = workspaceId,
            platformType = PlatformType.FACEBOOK,
            authorizationCode = code,
        )

        val result = facebookHandler.handleCallback(code, state, redirectUri)

        assertNotNull(result)
        assertEquals(socialAccount.id, result.socialAccountId)
        assertEquals(workspaceId, result.workspaceId)
        assertEquals("fb_user_456", result.platformUserId)
        assertEquals("testuser", result.username)
    }

    @Test
    fun `GoogleOAuthHandler returns OAuthResult with correct platform type`() {
        val code = "auth_code_456"
        val state = workspaceId.toString()
        val redirectUri = "https://example.com/oauth/google"

        val socialAccount = SocialAccount(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            credentialId = UUID.randomUUID(),
            platformType = PlatformType.GOOGLE_BUSINESS,
            platformUserId = "google_user_789",
            platformUsername = "googleuser",
            platformDisplayName = "Google User",
            platformAvatarUrl = null,
            profileUrl = null,
            isActive = true,
            metadata = emptyMap(),
            connectedAt = java.time.Instant.now(),
            lastSyncAt = java.time.Instant.now(),
        )

        Mockito.doReturn(socialAccount).`when`(connectSocialAccountUseCase).execute(
            workspaceId = workspaceId,
            platformType = PlatformType.GOOGLE_BUSINESS,
            authorizationCode = code,
        )

        val result = googleHandler.handleCallback(code, state, redirectUri)

        assertNotNull(result)
        assertEquals(socialAccount.id, result.socialAccountId)
        assertEquals(workspaceId, result.workspaceId)
        assertEquals("google_user_789", result.platformUserId)
        assertEquals("googleuser", result.username)
    }

    @Test
    fun `FacebookOAuthHandler has correct platform type`() {
        assertEquals(PlatformType.FACEBOOK, facebookHandler.platformType)
    }

    @Test
    fun `GoogleOAuthHandler has correct platform type`() {
        assertEquals(PlatformType.GOOGLE_BUSINESS, googleHandler.platformType)
    }
}