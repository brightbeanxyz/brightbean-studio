package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.OAuthConnection
import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.model.User
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class UserRepositoryTest {

    private lateinit var jdbi: Jdbi
    private lateinit var userRepo: JDBIUserRepository
    private lateinit var oauthRepo: JDBIOAuthConnectionRepository
    private lateinit var sessionRepo: JDBISessionRepository

    @BeforeEach
    fun setUp() {
        jdbi = Jdbi.create("jdbc:h2:mem:test_${UUID.randomUUID()};DB_CLOSE_DELAY=-1")
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())

        jdbi.useHandle<Exception> { handle ->
            handle.createUpdate("""
                CREATE TABLE accounts_user (
                    id UUID PRIMARY KEY,
                    email VARCHAR NOT NULL UNIQUE,
                    name VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    avatar VARCHAR,
                    totp_secret VARCHAR,
                    totp_recovery_codes TEXT,
                    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    last_workspace_id UUID,
                    tos_accepted_at TIMESTAMP,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE accounts_oauth_connection (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    provider VARCHAR NOT NULL,
                    provider_user_id VARCHAR NOT NULL,
                    provider_email VARCHAR,
                    created_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE accounts_session (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    token_hash VARCHAR NOT NULL,
                    device_info VARCHAR,
                    ip_address VARCHAR,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            """).execute()
        }

        userRepo = JDBIUserRepository(jdbi)
        oauthRepo = JDBIOAuthConnectionRepository(jdbi)
        sessionRepo = JDBISessionRepository(jdbi)
    }

    @Test
    fun `save and findById returns user`() {
        val user = createTestUser()
        userRepo.save(user)

        val found = userRepo.findById(user.id)

        assertNotNull(found)
        assertEquals(user.id, found!!.id)
        assertEquals(user.email, found.email)
        assertEquals(user.name, found.name)
        assertEquals(user.passwordHash, found.passwordHash)
    }

    @Test
    fun `findByEmail returns user`() {
        val user = createTestUser()
        userRepo.save(user)

        val found = userRepo.findByEmail(user.email)

        assertNotNull(found)
        assertEquals(user.id, found!!.id)
        assertEquals(user.email, found.email)
    }

    @Test
    fun `findByEmail returns null when not found`() {
        val found = userRepo.findByEmail("nobody@example.com")
        assertNull(found)
    }

    @Test
    fun `update persists changes`() {
        val user = createTestUser()
        userRepo.save(user)

        val updated = user.copy(name = "Updated Name", email = "updated@example.com")
        userRepo.update(updated)

        val found = userRepo.findById(user.id)
        assertNotNull(found)
        assertEquals("Updated Name", found!!.name)
        assertEquals("updated@example.com", found.email)
    }

    @Test
    fun `delete removes user`() {
        val user = createTestUser()
        userRepo.save(user)

        userRepo.delete(user.id)

        assertNull(userRepo.findById(user.id))
    }

    @Test
    fun `save and findById with totp recovery codes`() {
        val user = createTestUser(
            totpSecret = "secret",
            totpRecoveryCodes = listOf("code1", "code2"),
            totpEnabled = true
        )
        userRepo.save(user)

        val found = userRepo.findById(user.id)

        assertNotNull(found)
        assertEquals(listOf("code1", "code2"), found!!.totpRecoveryCodes)
        assertTrue(found.totpEnabled)
    }

    @Test
    fun `oauth save and findByProviderUser`() {
        val user = createTestUser()
        userRepo.save(user)

        val oauth = OAuthConnection(
            id = UUID.randomUUID(),
            userId = user.id,
            provider = "google",
            providerUserId = "google-123",
            providerEmail = "user@gmail.com",
        )
        oauthRepo.save(oauth)

        val found = oauthRepo.findByProviderUser("google", "google-123")

        assertNotNull(found)
        assertEquals(oauth.id, found!!.id)
        assertEquals("google", found.provider)
        assertEquals("google-123", found.providerUserId)
    }

    @Test
    fun `oauth findByUserIdAndProvider returns connection`() {
        val user = createTestUser()
        userRepo.save(user)

        val oauth = OAuthConnection(
            id = UUID.randomUUID(),
            userId = user.id,
            provider = "github",
            providerUserId = "gh-456",
        )
        oauthRepo.save(oauth)

        val found = oauthRepo.findByUserIdAndProvider(user.id, "github")

        assertNotNull(found)
        assertEquals(oauth.id, found!!.id)
    }

    @Test
    fun `session save and findByTokenHash`() {
        val user = createTestUser()
        userRepo.save(user)

        val session = Session(
            id = UUID.randomUUID(),
            userId = user.id,
            tokenHash = "hash123",
            deviceInfo = "Chrome/120",
            ipAddress = "127.0.0.1",
            expiresAt = Instant.now().plusSeconds(3600),
        )
        sessionRepo.save(session)

        val found = sessionRepo.findByTokenHash("hash123")

        assertNotNull(found)
        assertEquals(session.id, found!!.id)
        assertEquals("hash123", found.tokenHash)
        assertEquals("Chrome/120", found.deviceInfo)
        assertEquals("127.0.0.1", found.ipAddress)
    }

    @Test
    fun `session findActiveByUserId returns non-expired sessions`() {
        val user = createTestUser()
        userRepo.save(user)

        val activeSession = Session(
            id = UUID.randomUUID(),
            userId = user.id,
            tokenHash = "active-hash",
            expiresAt = Instant.now().plusSeconds(3600),
        )
        sessionRepo.save(activeSession)

        val sessions = sessionRepo.findActiveByUserId(user.id)

        assertEquals(1, sessions.size)
        assertEquals(activeSession.id, sessions[0].id)
    }

    @Test
    fun `session deleteByUserId removes all sessions`() {
        val user = createTestUser()
        userRepo.save(user)

        val s1 = Session(id = UUID.randomUUID(), userId = user.id, tokenHash = "h1", expiresAt = Instant.now().plusSeconds(3600))
        val s2 = Session(id = UUID.randomUUID(), userId = user.id, tokenHash = "h2", expiresAt = Instant.now().plusSeconds(3600))
        sessionRepo.save(s1)
        sessionRepo.save(s2)

        sessionRepo.deleteByUserId(user.id)

        assertNull(sessionRepo.findByTokenHash("h1"))
        assertNull(sessionRepo.findByTokenHash("h2"))
    }

    private fun createTestUser(
        totpSecret: String? = null,
        totpRecoveryCodes: List<String>? = null,
        totpEnabled: Boolean = false,
    ) = User(
        id = UUID.randomUUID(),
        email = "test-${UUID.randomUUID()}@example.com",
        name = "Test User",
        passwordHash = "\$2a\$10\$hashedpassword",
        totpSecret = totpSecret,
        totpRecoveryCodes = totpRecoveryCodes,
        totpEnabled = totpEnabled,
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    )
}
