package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApiKey
import com.brightbean.studio.domain.model.ApiKeyAuditLog
import com.brightbean.studio.domain.repository.ApiKeyAuditLogRepository
import com.brightbean.studio.domain.repository.ApiKeyRepository
import java.time.Instant
import java.util.UUID
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

data class IssuedApiKey(val apiKey: ApiKey, val rawToken: String)

class ApiKeyUseCases(
    private val apiKeyRepo: ApiKeyRepository,
    private val auditLogRepo: ApiKeyAuditLogRepository,
    private val secretKey: String,
) {
    fun issueApiKey(
        workspaceId: UUID,
        name: String,
        permissions: List<String>,
        socialAccountIds: List<UUID>,
        issuedBy: UUID?,
        expiresAt: Instant?,
    ): IssuedApiKey {
        val randomPart = generateRandomHex(32)
        val lookupPart = randomPart.take(8)
        val rawToken = "bb_studio_${randomPart}_${lookupPart}"
        val tokenHash = hmacSha256(rawToken)

        val apiKey = ApiKey(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = name,
            lookupPrefix = lookupPart,
            tokenHash = tokenHash,
            permissions = com.google.gson.Gson().toJson(permissions),
            socialAccountIds = com.google.gson.Gson().toJson(socialAccountIds.map { it.toString() }),
            issuedBy = issuedBy,
            expiresAt = expiresAt,
            revokedAt = null,
            lastUsedAt = null,
            lastUsedIp = null,
            rateOverrideWrites = null,
            rateOverrideReads = null,
            createdAt = Instant.now(),
        )
        apiKeyRepo.save(apiKey)
        return IssuedApiKey(apiKey, rawToken)
    }

    fun revokeApiKey(keyId: UUID) {
        val apiKey = apiKeyRepo.findById(keyId) ?: throw IllegalArgumentException("API key not found")
        apiKeyRepo.update(apiKey.copy(revokedAt = Instant.now()))
    }

    fun listApiKeys(workspaceId: UUID): List<ApiKey> = apiKeyRepo.findByWorkspaceId(workspaceId)

    fun verifyToken(rawToken: String): ApiKey? {
        if (!rawToken.startsWith("bb_studio_")) return null
        val parts = rawToken.split("_")
        if (parts.size < 3) return null
        val lookupPrefix = parts.last()
        val apiKey = apiKeyRepo.findActiveByLookupPrefix(lookupPrefix) ?: return null
        val computedHash = hmacSha256(rawToken)
        return if (computedHash == apiKey.tokenHash) apiKey else null
    }

    fun touchLastUsed(keyId: UUID, ip: String?) {
        val apiKey = apiKeyRepo.findById(keyId) ?: return
        apiKeyRepo.update(apiKey.copy(lastUsedAt = Instant.now(), lastUsedIp = ip))
    }

    fun createAuditLog(
        apiKeyId: UUID,
        action: String,
        targetId: UUID?,
        method: String,
        path: String,
        statusCode: Int,
        ip: String?,
        userAgent: String,
    ): ApiKeyAuditLog {
        val log = ApiKeyAuditLog(
            id = UUID.randomUUID(),
            apiKeyId = apiKeyId,
            action = action,
            targetId = targetId,
            method = method,
            path = path,
            statusCode = statusCode,
            ip = ip,
            userAgent = userAgent,
            createdAt = Instant.now(),
        )
        return auditLogRepo.save(log)
    }

    private fun hmacSha256(input: String): String {
        val mac = Mac.getInstance("HmacSHA256")
        val keySpec = SecretKeySpec(secretKey.toByteArray(Charsets.UTF_8), "HmacSHA256")
        mac.init(keySpec)
        val hash = mac.doFinal(input.toByteArray(Charsets.UTF_8))
        return hash.joinToString("") { "%02x".format(it) }
    }

    private fun generateRandomHex(bytes: Int): String {
        val random = java.security.SecureRandom()
        val buf = ByteArray(bytes)
        random.nextBytes(buf)
        return buf.joinToString("") { "%02x".format(it) }
    }
}
