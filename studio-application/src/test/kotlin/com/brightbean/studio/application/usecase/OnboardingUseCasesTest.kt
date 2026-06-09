package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ConnectionLink
import com.brightbean.studio.domain.model.ConnectionLinkUsage
import com.brightbean.studio.domain.model.OnboardingChecklist
import com.brightbean.studio.domain.repository.ConnectionLinkRepository
import com.brightbean.studio.domain.repository.ConnectionLinkUsageRepository
import com.brightbean.studio.domain.repository.OnboardingChecklistRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class OnboardingUseCasesTest {

    private lateinit var linkRepo: InMemConnectionLinkRepo
    private lateinit var usageRepo: InMemConnectionLinkUsageRepo
    private lateinit var checklistRepo: InMemOnboardingChecklistRepo
    private lateinit var useCases: OnboardingUseCases

    @BeforeEach
    fun setUp() {
        linkRepo = InMemConnectionLinkRepo()
        usageRepo = InMemConnectionLinkUsageRepo()
        checklistRepo = InMemOnboardingChecklistRepo()
        useCases = OnboardingUseCases(linkRepo, usageRepo, checklistRepo)
    }

    @Test
    fun `createConnectionLink creates active link`() {
        val workspaceId = UUID.randomUUID()
        val expiresAt = Instant.now().plusSeconds(86400)
        val link = useCases.createConnectionLink(workspaceId, null, expiresAt)
        assertEquals(workspaceId, link.workspaceId)
        assertTrue(link.isActive)
    }

    @Test
    fun `revokeConnectionLink sets revokedAt`() {
        val link = useCases.createConnectionLink(UUID.randomUUID(), null, Instant.now().plusSeconds(86400))
        linkRepo.data[link.token] = link
        useCases.revokeConnectionLink(link.id)
        assertTrue(linkRepo.data[link.token]!!.isRevoked)
    }

    @Test
    fun `validateConnectionLink returns link if active`() {
        val link = useCases.createConnectionLink(UUID.randomUUID(), null, Instant.now().plusSeconds(86400))
        val validated = useCases.validateConnectionLink(link.token)
        assertNotNull(validated)
        assertEquals(link.id, validated!!.id)
    }

    @Test
    fun `validateConnectionLink returns null if expired`() {
        val expiredLink = linkRepo.save(ConnectionLink(
            id = UUID.randomUUID(),
            workspaceId = UUID.randomUUID(),
            token = UUID.randomUUID().toString(),
            createdBy = null,
            expiresAt = Instant.now().minusSeconds(60),
            revokedAt = null,
            createdAt = Instant.now(),
        ))
        assertNull(useCases.validateConnectionLink(expiredLink.token))
    }

    @Test
    fun `recordConnectionUsage saves usage`() {
        val linkId = UUID.randomUUID()
        val socialAccountId = UUID.randomUUID()
        val usage = useCases.recordConnectionUsage(linkId, socialAccountId)
        assertEquals(linkId, usage.connectionLinkId)
        assertEquals(socialAccountId, usage.socialAccountId)
    }

    @Test
    fun `getChecklist creates checklist if not exists`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val checklist = useCases.getChecklist(userId, workspaceId)
        assertNotNull(checklist)
        assertFalse(checklist.isDismissed)
    }

    @Test
    fun `getChecklist returns existing checklist`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val first = useCases.getChecklist(userId, workspaceId)
        val second = useCases.getChecklist(userId, workspaceId)
        assertEquals(first.id, second.id)
    }

    @Test
    fun `dismissChecklist sets dismissed`() {
        val userId = UUID.randomUUID()
        val workspaceId = UUID.randomUUID()
        val checklist = useCases.dismissChecklist(userId, workspaceId)
        assertTrue(checklist.isDismissed)
        assertNotNull(checklist.dismissedAt)
    }

    class InMemConnectionLinkRepo : ConnectionLinkRepository {
        val data = mutableMapOf<String, ConnectionLink>()

        override fun findById(id: UUID): ConnectionLink? = data.values.find { it.id == id }
        override fun findByToken(token: String): ConnectionLink? = data[token]
        override fun findByWorkspaceId(workspaceId: UUID): List<ConnectionLink> = data.values.filter { it.workspaceId == workspaceId }
        override fun save(link: ConnectionLink): ConnectionLink = link.also { data[link.token] = it }
        override fun update(link: ConnectionLink): ConnectionLink = link.also { data[link.token] = it }
    }

    class InMemConnectionLinkUsageRepo : ConnectionLinkUsageRepository {
        private val items = mutableListOf<ConnectionLinkUsage>()
        override fun findByConnectionLinkId(connectionLinkId: UUID): List<ConnectionLinkUsage> = items.filter { it.connectionLinkId == connectionLinkId }
        override fun save(usage: ConnectionLinkUsage): ConnectionLinkUsage = usage.also { items.add(it) }
    }

    class InMemOnboardingChecklistRepo : OnboardingChecklistRepository {
        private val data = mutableMapOf<String, OnboardingChecklist>()
        override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): OnboardingChecklist? = data["$userId:$workspaceId"]
        override fun save(checklist: OnboardingChecklist): OnboardingChecklist = checklist.also { data["${it.userId}:${it.workspaceId}"] = it }
        override fun update(checklist: OnboardingChecklist): OnboardingChecklist = checklist.also { data["${it.userId}:${it.workspaceId}"] = it }
    }
}
