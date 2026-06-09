package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(SocialAccountDto::class)
interface SocialAccountDao {
    @SqlQuery("SELECT * FROM social_account WHERE id = :id")
    fun findById(id: UUID): SocialAccountDto?

    @SqlQuery("SELECT * FROM social_account WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<SocialAccountDto>

    @SqlQuery("SELECT * FROM social_account WHERE workspace_id = :workspaceId AND platform_type = :platformType")
    fun findByPlatform(workspaceId: UUID, platformType: String): List<SocialAccountDto>

    @SqlQuery("SELECT * FROM social_account WHERE workspace_id = :workspaceId AND is_active = true")
    fun findActiveByWorkspace(workspaceId: UUID): List<SocialAccountDto>

    @SqlUpdate("""
        INSERT INTO social_account (id, workspace_id, credential_id, platform_type, platform_user_id, platform_username, platform_display_name, platform_avatar_url, profile_url, is_active, connection_status, last_health_check_at, last_error, follower_count, instance_url, daily_post_limit_override, analytics_needs_reconnect, metadata, connected_at, last_sync_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.credentialId, :dto.platformType, :dto.platformUserId, :dto.platformUsername, :dto.platformDisplayName, :dto.platformAvatarUrl, :dto.profileUrl, :dto.isActive, :dto.connectionStatus, :dto.lastHealthCheckAt, :dto.lastError, :dto.followerCount, :dto.instanceUrl, :dto.dailyPostLimitOverride, :dto.analyticsNeedsReconnect, :dto.metadata, :dto.connectedAt, :dto.lastSyncAt)
    """)
    fun insert(dto: SocialAccountDto)

    @SqlUpdate("""
        UPDATE social_account SET
            platform_username = :dto.platformUsername,
            platform_display_name = :dto.platformDisplayName,
            platform_avatar_url = :dto.platformAvatarUrl,
            profile_url = :dto.profileUrl,
            is_active = :dto.isActive,
            connection_status = :dto.connectionStatus,
            last_health_check_at = :dto.lastHealthCheckAt,
            last_error = :dto.lastError,
            follower_count = :dto.followerCount,
            instance_url = :dto.instanceUrl,
            daily_post_limit_override = :dto.dailyPostLimitOverride,
            analytics_needs_reconnect = :dto.analyticsNeedsReconnect,
            metadata = :dto.metadata,
            last_sync_at = :dto.lastSyncAt
        WHERE id = :dto.id
    """)
    fun update(dto: SocialAccountDto)

    @SqlUpdate("DELETE FROM social_account WHERE id = :id")
    fun delete(id: UUID)
}

data class SocialAccountDto(
    val id: UUID,
    val workspaceId: UUID,
    val credentialId: UUID,
    val platformType: String,
    val platformUserId: String,
    val platformUsername: String,
    val platformDisplayName: String,
    val platformAvatarUrl: String?,
    val profileUrl: String?,
    val isActive: Boolean,
    val connectionStatus: String,
    val lastHealthCheckAt: java.time.Instant?,
    val lastError: String?,
    val followerCount: Int,
    val instanceUrl: String?,
    val dailyPostLimitOverride: Int?,
    val analyticsNeedsReconnect: Boolean,
    val metadata: String,
    val connectedAt: java.time.Instant,
    val lastSyncAt: java.time.Instant?,
)
