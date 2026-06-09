package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ConnectionLinkUsage
import java.util.UUID

interface ConnectionLinkUsageRepository {
    fun findByConnectionLinkId(connectionLinkId: UUID): List<ConnectionLinkUsage>
    fun save(usage: ConnectionLinkUsage): ConnectionLinkUsage
}
