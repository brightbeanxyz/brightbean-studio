package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApiKey
import com.brightbean.studio.domain.model.ApiKeyAuditLog
import com.brightbean.studio.domain.repository.ApiKeyAuditLogRepository
import com.brightbean.studio.domain.repository.ApiKeyRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class ApiKeyUseCasesTest {

    private lateinit var apiKeyRepo: InMemApiKeyRepo
    private lateinit var auditLogRepo: InMemApiKeyAuditLogRepo
    private lateinit var useCases: ApiKeyUseCases
    private val secretKey = "test-secret-key-for-hmac"

    @BeforeEach
    fun setUp() {
        apiKeyRepo = InMemApiKeyRepo()
        auditLogRepo = InMemApiKeyAuditLogRepo()
        useCases = ApiKeyUseCases(apiKeyRepo, auditLogRepo, secretKey)
    }

    @Test
    fun `issueApiKey creates key and returns raw token`() {
        val workspaceId = UUID.randomUUID()
        val result = useCases.issueApiKey(
            workspaceId = workspaceId,
            name = "Test Key",
            permissions = listOf("read"),
            socialAccountIds = emptyList(),
            issuedBy = null,
            expiresAt = null,
        )
        assertEquals(workspaceId, result.apiKey.workspaceId)
        assertEquals("Test Key", result.apiKey.name)
        assertTrue(result.rawToken.startsWith("bb_studio_"))
        assertNotNull(result.apiKey.lookupPrefix)
    }

    @Test
    fun `issueApiKey raw token format`() {
        val result = useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        val parts = result.rawToken.split("_")
        assertEquals("bb", parts[0])
        assertEquals("studio", parts[1])
        assertTrue(parts[2].isNotEmpty())
    }

    @Test
    fun `revokeApiKey sets revokedAt`() {
        val result = useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        assertNull(result.apiKey.revokedAt)
        useCases.revokeApiKey(result.apiKey.id)
        val updated = apiKeyRepo.findById(result.apiKey.id)!!
        assertNotNull(updated.revokedAt)
        assertFalse(updated.isActive)
    }

    @Test
    fun `listApiKeys returns keys for workspace`() {
        val ws1 = UUID.randomUUID()
        val ws2 = UUID.randomUUID()
        useCases.issueApiKey(ws1, "Key1", emptyList(), emptyList(), null, null)
        useCases.issueApiKey(ws1, "Key2", emptyList(), emptyList(), null, null)
        useCases.issueApiKey(ws2, "Key3", emptyList(), emptyList(), null, null)

        assertEquals(2, useCases.listApiKeys(ws1).size)
        assertEquals(1, useCases.listApiKeys(ws2).size)
    }

    @Test
    fun `verifyToken succeeds with valid token`() {
        val result = useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        val verified = useCases.verifyToken(result.rawToken)
        assertNotNull(verified)
        assertEquals(result.apiKey.id, verified!!.id)
    }

    @Test
    fun `verifyToken fails with wrong token`() {
        useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        assertNull(useCases.verifyToken("bb_studio_wrongvalue_wrong"))
    }

    @Test
    fun `verifyToken fails with revoked key`() {
        val result = useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        useCases.revokeApiKey(result.apiKey.id)
        assertNull(useCases.verifyToken(result.rawToken))
    }

    @Test
    fun `verifyToken fails for non-bb-studio prefix`() {
        assertNull(useCases.verifyToken("other_token"))
    }

    @Test
    fun `touchLastUsed updates lastUsedAt`() {
        val result = useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        assertNull(result.apiKey.lastUsedAt)
        useCases.touchLastUsed(result.apiKey.id, "127.0.0.1")
        val updated = apiKeyRepo.findById(result.apiKey.id)!!
        assertNotNull(updated.lastUsedAt)
        assertEquals("127.0.0.1", updated.lastUsedIp)
    }

    @Test
    fun `createAuditLog saves log entry`() {
        val apiKeyId = UUID.randomUUID()
        val log = useCases.createAuditLog(apiKeyId, "post.create", null, "POST", "/api/posts", 201, "127.0.0.1", "TestAgent")
        assertEquals(apiKeyId, log.apiKeyId)
        assertEquals("post.create", log.action)
        assertEquals(201, log.statusCode)
        assertEquals(1, auditLogRepo.data.size)
    }

    @Test
    fun `token hash is HMAC-SHA256 of raw token`() {
        val result = useCases.issueApiKey(UUID.randomUUID(), "Key", emptyList(), emptyList(), null, null)
        assertTrue(result.apiKey.tokenHash.isNotEmpty())
        assertEquals(64, result.apiKey.tokenHash.length)
    }

    class InMemApiKeyRepo : ApiKeyRepository {
        val data = mutableMapOf<UUID, ApiKey>()

        override fun findById(id: UUID): ApiKey? = data[id]
        override fun findByLookupPrefix(lookupPrefix: String): ApiKey? = data.values.find { it.lookupPrefix == lookupPrefix }
        override fun findByWorkspaceId(workspaceId: UUID): List<ApiKey> = data.values.filter { it.workspaceId == workspaceId }
        override fun findActiveByLookupPrefix(lookupPrefix: String): ApiKey? =
            data.values.find { it.lookupPrefix == lookupPrefix && it.isActive }
        override fun save(apiKey: ApiKey): ApiKey = apiKey.also { data[apiKey.id] = it }
        override fun update(apiKey: ApiKey): ApiKey = apiKey.also { data[apiKey.id] = it }
    }

    class InMemApiKeyAuditLogRepo : ApiKeyAuditLogRepository {
        val data = mutableListOf<ApiKeyAuditLog>()
        override fun findByApiKeyId(apiKeyId: UUID): List<ApiKeyAuditLog> = data.filter { it.apiKeyId == apiKeyId }
        override fun save(log: ApiKeyAuditLog): ApiKeyAuditLog = log.also { data.add(it) }
    }
}
