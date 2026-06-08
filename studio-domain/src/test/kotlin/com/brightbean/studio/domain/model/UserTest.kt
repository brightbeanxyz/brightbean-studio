package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class UserTest {

    @Test
    fun `user has required fields`() {
        val now = Instant.now()
        val user = User(
            id = UUID.randomUUID(),
            email = "test@example.com",
            name = "Test User",
            passwordHash = "hashed",
            isActive = true,
            createdAt = now,
            updatedAt = now,
        )
        assertEquals("test@example.com", user.email)
        assertEquals("Test User", user.name)
        assertTrue(user.isActive)
        assertFalse(user.totpEnabled)
        assertNull(user.totpSecret)
        assertNull(user.avatar)
        assertNull(user.lastWorkspaceId)
    }

    @Test
    fun `session has token hash and expiry`() {
        val now = Instant.now()
        val session = Session(
            id = UUID.randomUUID(),
            userId = UUID.randomUUID(),
            tokenHash = "abc123hash",
            expiresAt = now.plusSeconds(86400),
            createdAt = now,
        )
        assertEquals("abc123hash", session.tokenHash)
        assertTrue(session.expiresAt.isAfter(now))
    }
}
