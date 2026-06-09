package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.ApiKey
import com.brightbean.studio.domain.model.ApiKeyAuditLog
import com.brightbean.studio.domain.repository.ApiKeyAuditLogRepository
import com.brightbean.studio.domain.repository.ApiKeyRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIApiKeyRepository(jdbi: Jdbi) : ApiKeyRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: ApiKeyDao by lazy { jdbi.onDemand(ApiKeyDao::class.java) }

    override fun findById(id: UUID): ApiKey? = dao.findById(id)?.toDomain()
    override fun findByLookupPrefix(lookupPrefix: String): ApiKey? = dao.findByLookupPrefix(lookupPrefix)?.toDomain()
    override fun findByWorkspaceId(workspaceId: UUID): List<ApiKey> = dao.findByWorkspaceId(workspaceId).map { it.toDomain() }
    override fun findActiveByLookupPrefix(lookupPrefix: String): ApiKey? = dao.findActiveByLookupPrefix(lookupPrefix)?.toDomain()
    override fun save(apiKey: ApiKey): ApiKey { dao.insert(apiKey.toDto()); return apiKey }
    override fun update(apiKey: ApiKey): ApiKey { dao.update(apiKey.toDto()); return apiKey }

    private fun ApiKey.toDto() = ApiKeyDto(id, workspaceId, name, lookupPrefix, tokenHash, permissions, socialAccountIds, issuedBy, expiresAt, revokedAt, lastUsedAt, lastUsedIp, rateOverrideWrites, rateOverrideReads, createdAt)
    private fun ApiKeyDto.toDomain() = ApiKey(id, workspaceId, name, lookupPrefix, tokenHash, permissions, socialAccountIds, issuedBy, expiresAt, revokedAt, lastUsedAt, lastUsedIp, rateOverrideWrites, rateOverrideReads, createdAt)
}

class JDBIApiKeyAuditLogRepository(jdbi: Jdbi) : ApiKeyAuditLogRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: ApiKeyAuditLogDao by lazy { jdbi.onDemand(ApiKeyAuditLogDao::class.java) }

    override fun findByApiKeyId(apiKeyId: UUID): List<ApiKeyAuditLog> = dao.findByApiKeyId(apiKeyId).map { it.toDomain() }
    override fun save(log: ApiKeyAuditLog): ApiKeyAuditLog { dao.insert(log.toDto()); return log }

    private fun ApiKeyAuditLog.toDto() = ApiKeyAuditLogDto(id, apiKeyId, action, targetId, method, path, statusCode, ip, userAgent, createdAt)
    private fun ApiKeyAuditLogDto.toDomain() = ApiKeyAuditLog(id, apiKeyId, action, targetId, method, path, statusCode, ip, userAgent, createdAt)
}
