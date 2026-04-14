package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.PlatformType
import java.util.UUID

interface CredentialRepository {
    fun findById(id: UUID): Credential?
    fun findByWorkspaceId(workspaceId: UUID): List<Credential>
    fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): Credential?
    fun save(credential: Credential): Credential
    fun update(credential: Credential): Credential
    fun delete(id: UUID)
}
