package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ConnectionLink
import java.util.UUID

interface ConnectionLinkRepository {
    fun findById(id: UUID): ConnectionLink?
    fun findByToken(token: String): ConnectionLink?
    fun findByWorkspaceId(workspaceId: UUID): List<ConnectionLink>
    fun save(link: ConnectionLink): ConnectionLink
    fun update(link: ConnectionLink): ConnectionLink
}
