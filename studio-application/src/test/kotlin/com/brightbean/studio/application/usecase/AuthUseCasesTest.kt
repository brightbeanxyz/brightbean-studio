package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.UserRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class AuthUseCasesTest {

    private lateinit var userRepository: InMemoryUserRepository
    private lateinit var sessionRepository: InMemorySessionRepository
    private lateinit var authUseCases: AuthUseCases

    @BeforeEach
    fun setUp() {
        userRepository = InMemoryUserRepository()
        sessionRepository = InMemorySessionRepository()
        authUseCases = AuthUseCases(userRepository, sessionRepository)
    }

    @Test
    fun `register creates user with hashed password`() {
        val result = authUseCases.register("test@example.com", "Test User", "password123")
        assertTrue(result.isSuccess)
        val user = result.getOrThrow()
        assertEquals("test@example.com", user.email)
        assertTrue(user.passwordHash.startsWith("\$2"))
    }

    @Test
    fun `register rejects duplicate email`() {
        authUseCases.register("test@example.com", "User 1", "password123")
        val result = authUseCases.register("test@example.com", "User 2", "password456")
        assertTrue(result.isFailure)
    }

    @Test
    fun `login with valid credentials returns session token`() {
        authUseCases.register("test@example.com", "Test User", "password123")
        val result = authUseCases.login("test@example.com", "password123")
        assertTrue(result.isSuccess)
        val token = result.getOrThrow()
        assertNotNull(token)
        assertTrue(token.isNotEmpty())
    }

    @Test
    fun `login with wrong password fails`() {
        authUseCases.register("test@example.com", "Test User", "password123")
        val result = authUseCases.login("test@example.com", "wrongpassword")
        assertTrue(result.isFailure)
    }

    @Test
    fun `login with nonexistent email fails`() {
        val result = authUseCases.login("nobody@example.com", "password123")
        assertTrue(result.isFailure)
    }

    @Test
    fun `verifySession returns user for valid token`() {
        authUseCases.register("test@example.com", "Test User", "password123")
        val token = authUseCases.login("test@example.com", "password123").getOrThrow()
        val user = authUseCases.verifySession(token)
        assertNotNull(user)
        assertEquals("test@example.com", user!!.email)
    }

    @Test
    fun `verifySession returns null for invalid token`() {
        assertNull(authUseCases.verifySession("invalid-token"))
    }

    @Test
    fun `logout deletes session`() {
        authUseCases.register("test@example.com", "Test User", "password123")
        val token = authUseCases.login("test@example.com", "password123").getOrThrow()
        authUseCases.logout(token)
        assertNull(authUseCases.verifySession(token))
    }

    private class InMemoryUserRepository : UserRepository {
        private val users = mutableMapOf<UUID, User>()
        override fun findById(id: UUID) = users[id]
        override fun findByEmail(email: String) = users.values.find { it.email == email }
        override fun save(user: User): User { users[user.id] = user; return user }
        override fun update(user: User): User { users[user.id] = user; return user }
        override fun delete(id: UUID) { users.remove(id) }
    }

    private class InMemorySessionRepository : SessionRepository {
        private val sessions = mutableMapOf<UUID, Session>()
        override fun findById(id: UUID) = sessions[id]
        override fun findByTokenHash(tokenHash: String) = sessions.values.find { it.tokenHash == tokenHash }
        override fun findActiveByUserId(userId: UUID) = sessions.values.filter { it.userId == userId && !it.isExpired }
        override fun save(session: Session): Session { sessions[session.id] = session; return session }
        override fun delete(id: UUID) { sessions.remove(id) }
        override fun deleteByUserId(userId: UUID) { sessions.entries.removeIf { it.value.userId == userId } }
    }
}
