package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ApiKey
import java.util.UUID

interface ApiKeyRepository {
    fun findById(id: UUID): ApiKey?
    fun findByLookupPrefix(lookupPrefix: String): ApiKey?
    fun findByWorkspaceId(workspaceId: UUID): List<ApiKey>
    fun findActiveByLookupPrefix(lookupPrefix: String): ApiKey?
    fun save(apiKey: ApiKey): ApiKey
    fun update(apiKey: ApiKey): ApiKey
}
