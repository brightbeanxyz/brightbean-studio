package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.ConnectionStatus
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBISocialAccountRepository(jdbi: Jdbi) : SocialAccountRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: SocialAccountDao by lazy { jdbi.onDemand(SocialAccountDao::class.java) }

    override fun findById(id: UUID): SocialAccount? =
        dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<SocialAccount> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): List<SocialAccount> =
        dao.findByPlatform(workspaceId, platformType.name).map { it.toDomain() }

    override fun findActiveByWorkspace(workspaceId: UUID): List<SocialAccount> =
        dao.findActiveByWorkspace(workspaceId).map { it.toDomain() }

    override fun save(socialAccount: SocialAccount): SocialAccount {
        dao.insert(socialAccount.toDto())
        return socialAccount
    }

    override fun update(socialAccount: SocialAccount): SocialAccount {
        dao.update(socialAccount.toDto())
        return socialAccount
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun SocialAccount.toDto() = SocialAccountDto(
        id = id,
        workspaceId = workspaceId,
        credentialId = credentialId,
        platformType = platformType.name,
        platformUserId = platformUserId,
        platformUsername = platformUsername,
        platformDisplayName = platformDisplayName,
        platformAvatarUrl = platformAvatarUrl,
        profileUrl = profileUrl,
        isActive = isActive,
        connectionStatus = connectionStatus.name,
        lastHealthCheckAt = lastHealthCheckAt,
        lastError = lastError,
        followerCount = followerCount,
        instanceUrl = instanceUrl,
        dailyPostLimitOverride = dailyPostLimitOverride,
        analyticsNeedsReconnect = analyticsNeedsReconnect,
        metadata = objectMapper.writeValueAsString(metadata),
        connectedAt = connectedAt,
        lastSyncAt = lastSyncAt,
    )

    private fun SocialAccountDto.toDomain(): SocialAccount {
        val meta: Map<String, String> = try {
            objectMapper.readValue(metadata, objectMapper.typeFactory.constructMapType(Map::class.java, String::class.java, String::class.java))
        } catch (_: Exception) {
            emptyMap()
        }
        return SocialAccount(
            id = id,
            workspaceId = workspaceId,
            credentialId = credentialId,
            platformType = PlatformType.valueOf(platformType),
            platformUserId = platformUserId,
            platformUsername = platformUsername,
            platformDisplayName = platformDisplayName,
            platformAvatarUrl = platformAvatarUrl,
            profileUrl = profileUrl,
            isActive = isActive,
            connectionStatus = ConnectionStatus.valueOf(connectionStatus),
            lastHealthCheckAt = lastHealthCheckAt,
            lastError = lastError,
            followerCount = followerCount,
            instanceUrl = instanceUrl,
            dailyPostLimitOverride = dailyPostLimitOverride,
            analyticsNeedsReconnect = analyticsNeedsReconnect,
            metadata = meta,
            connectedAt = connectedAt,
            lastSyncAt = lastSyncAt,
        )
    }
}
