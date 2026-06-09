package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.InboxSLAConfig
import java.util.UUID

interface InboxSLAConfigRepository {
    fun findByWorkspaceId(workspaceId: UUID): InboxSLAConfig?
    fun save(config: InboxSLAConfig): InboxSLAConfig
    fun update(config: InboxSLAConfig): InboxSLAConfig
}
