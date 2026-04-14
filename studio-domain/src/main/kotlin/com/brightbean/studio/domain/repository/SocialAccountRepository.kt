package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import java.util.UUID

interface SocialAccountRepository {
    fun findById(id: UUID): SocialAccount?
    fun findByWorkspaceId(workspaceId: UUID): List<SocialAccount>
    fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): List<SocialAccount>
    fun findActiveByWorkspace(workspaceId: UUID): List<SocialAccount>
    fun save(socialAccount: SocialAccount): SocialAccount
    fun update(socialAccount: SocialAccount): SocialAccount
    fun delete(id: UUID)
}
