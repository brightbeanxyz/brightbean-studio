package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ApiKeyAuditLog
import java.util.UUID

interface ApiKeyAuditLogRepository {
    fun findByApiKeyId(apiKeyId: UUID): List<ApiKeyAuditLog>
    fun save(log: ApiKeyAuditLog): ApiKeyAuditLog
}
