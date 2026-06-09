package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.MagicLinkToken
import com.brightbean.studio.domain.repository.MagicLinkTokenRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class ClientPortalUseCasesTest {

    private lateinit var repo: InMemMagicLinkTokenRepo
    private lateinit var useCases: ClientPortalUseCases

    @BeforeEach
    fun setUp() {
        repo = InMemMagicLinkTokenRepo()
        useCases = ClientPortalUseCases(repo)
    }

    @Test
    fun `generateMagicLink creates token and invalidates prior`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val token1 = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())
        val token2 = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())

        assertNotNull(token1)
        assertNotNull(token2)
        val peeked = repo.findByToken(token1.token)
        assertTrue(peeked!!.isConsumed)
    }

    @Test
    fun `peekMagicLink returns token if valid`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val token = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())

        val peeked = useCases.peekMagicLink(token.token)
        assertNotNull(peeked)
        assertEquals(token.token, peeked!!.token)
    }

    @Test
    fun `peekMagicLink returns null for consumed token`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val token = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())

        useCases.consumeMagicLink(token.token)
        assertNull(useCases.peekMagicLink(token.token))
    }

    @Test
    fun `consumeMagicLink returns valid result on first use`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val token = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())

        val result = useCases.consumeMagicLink(token.token)
        assertTrue(result.isValid)
        assertEquals(userId, result.userId)
        assertEquals(workspaceId, result.workspaceId)
    }

    @Test
    fun `consumeMagicLink returns invalid on second use`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val token = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())

        useCases.consumeMagicLink(token.token)
        val result = useCases.consumeMagicLink(token.token)
        assertFalse(result.isValid)
    }

    @Test
    fun `consumeMagicLink returns invalid for unknown token`() {
        val result = useCases.consumeMagicLink("nonexistent")
        assertFalse(result.isValid)
    }

    @Test
    fun `revokeMagicLink expires token`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val token = useCases.generateMagicLink(workspaceId, userId, UUID.randomUUID())

        useCases.revokeMagicLink(UUID.fromString(token.token), workspaceId)
        assertNull(useCases.peekMagicLink(token.token))
    }

    class InMemMagicLinkTokenRepo : MagicLinkTokenRepository {
        private val items = mutableMapOf<String, MagicLinkToken>()

        override fun findByToken(token: String): MagicLinkToken? = items[token]
        override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): List<MagicLinkToken> =
            items.values.filter { it.userId == userId && it.workspaceId == workspaceId }
        override fun save(token: MagicLinkToken): MagicLinkToken = token.also { items[token.token] = it }
        override fun update(token: MagicLinkToken): MagicLinkToken = token.also { items[token.token] = it }
        override fun revokeAllForUserAndWorkspace(userId: UUID, workspaceId: UUID) {
            items.values.filter { it.userId == userId && it.workspaceId == workspaceId }.forEach {
                items[it.token] = it.copy(isConsumed = true, expiresAt = Instant.now())
            }
        }
    }
}
