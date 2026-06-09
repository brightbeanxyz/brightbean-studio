package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.time.LocalDate
import java.util.UUID

@RegisterKotlinMapper(AccountInsightsSnapshotDto::class)
interface AccountInsightsSnapshotDao {
    @SqlQuery("SELECT * FROM analytics_account_insights_snapshot WHERE social_account_id = :socialAccountId AND date BETWEEN :from AND :to ORDER BY date")
    fun findBySocialAccountAndDateRange(socialAccountId: UUID, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshotDto>

    @SqlQuery("SELECT * FROM analytics_account_insights_snapshot WHERE social_account_id = :socialAccountId AND metric_key = :metricKey AND date BETWEEN :from AND :to ORDER BY date")
    fun findBySocialAccountAndMetricKeyAndDateRange(socialAccountId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<AccountInsightsSnapshotDto>

    @SqlUpdate("""
        INSERT INTO analytics_account_insights_snapshot (id, social_account_id, metric_key, date, value, captured_at)
        VALUES (:dto.id, :dto.socialAccountId, :dto.metricKey, :dto.date, :dto.value, :dto.capturedAt)
        ON CONFLICT (social_account_id, metric_key, date) DO UPDATE SET value = EXCLUDED.value, captured_at = EXCLUDED.captured_at
    """)
    fun upsert(dto: AccountInsightsSnapshotDto)
}

data class AccountInsightsSnapshotDto(
    val id: UUID,
    val socialAccountId: UUID,
    val metricKey: String,
    val date: LocalDate,
    val value: Double,
    val capturedAt: Instant,
)

@RegisterKotlinMapper(PostInsightsSnapshotDto::class)
interface PostInsightsSnapshotDao {
    @SqlQuery("SELECT * FROM analytics_post_insights_snapshot WHERE platform_post_id = :platformPostId AND date BETWEEN :from AND :to ORDER BY date")
    fun findByPlatformPostAndDateRange(platformPostId: UUID, from: LocalDate, to: LocalDate): List<PostInsightsSnapshotDto>

    @SqlQuery("SELECT * FROM analytics_post_insights_snapshot WHERE platform_post_id = :platformPostId AND metric_key = :metricKey AND date BETWEEN :from AND :to ORDER BY date")
    fun findByPlatformPostAndMetricKeyAndDateRange(platformPostId: UUID, metricKey: String, from: LocalDate, to: LocalDate): List<PostInsightsSnapshotDto>

    @SqlUpdate("""
        INSERT INTO analytics_post_insights_snapshot (id, platform_post_id, metric_key, date, value, captured_at)
        VALUES (:dto.id, :dto.platformPostId, :dto.metricKey, :dto.date, :dto.value, :dto.capturedAt)
        ON CONFLICT (platform_post_id, metric_key, date) DO UPDATE SET value = EXCLUDED.value, captured_at = EXCLUDED.captured_at
    """)
    fun upsert(dto: PostInsightsSnapshotDto)
}

data class PostInsightsSnapshotDto(
    val id: UUID,
    val platformPostId: UUID,
    val metricKey: String,
    val date: LocalDate,
    val value: Double,
    val capturedAt: Instant,
)

@RegisterKotlinMapper(MagicLinkTokenDto::class)
interface MagicLinkTokenDao {
    @SqlQuery("SELECT * FROM client_portal_magic_link_token WHERE token = :token")
    fun findByToken(token: String): MagicLinkTokenDto?

    @SqlQuery("SELECT * FROM client_portal_magic_link_token WHERE user_id = :userId AND workspace_id = :workspaceId")
    fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): List<MagicLinkTokenDto>

    @SqlUpdate("""
        INSERT INTO client_portal_magic_link_token (id, user_id, workspace_id, token, created_at, expires_at, last_used_at, is_consumed)
        VALUES (:dto.id, :dto.userId, :dto.workspaceId, :dto.token, :dto.createdAt, :dto.expiresAt, :dto.lastUsedAt, :dto.isConsumed)
    """)
    fun insert(dto: MagicLinkTokenDto)

    @SqlUpdate("""
        UPDATE client_portal_magic_link_token SET last_used_at = :dto.lastUsedAt, is_consumed = :dto.isConsumed
        WHERE id = :dto.id
    """)
    fun update(dto: MagicLinkTokenDto)

    @SqlUpdate("UPDATE client_portal_magic_link_token SET is_consumed = true, expires_at = NOW() WHERE user_id = :userId AND workspace_id = :workspaceId")
    fun revokeAllForUserAndWorkspace(userId: UUID, workspaceId: UUID)
}

data class MagicLinkTokenDto(
    val id: UUID,
    val userId: UUID,
    val workspaceId: UUID,
    val token: String,
    val createdAt: Instant,
    val expiresAt: Instant,
    val lastUsedAt: Instant?,
    val isConsumed: Boolean,
)

@RegisterKotlinMapper(ConnectionLinkDto::class)
interface ConnectionLinkDao {
    @SqlQuery("SELECT * FROM onboarding_connection_link WHERE id = :id")
    fun findById(id: UUID): ConnectionLinkDto?

    @SqlQuery("SELECT * FROM onboarding_connection_link WHERE token = :token")
    fun findByToken(token: String): ConnectionLinkDto?

    @SqlQuery("SELECT * FROM onboarding_connection_link WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<ConnectionLinkDto>

    @SqlUpdate("""
        INSERT INTO onboarding_connection_link (id, workspace_id, token, created_by, expires_at, revoked_at, created_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.token, :dto.createdBy, :dto.expiresAt, :dto.revokedAt, :dto.createdAt)
    """)
    fun insert(dto: ConnectionLinkDto)

    @SqlUpdate("""
        UPDATE onboarding_connection_link SET revoked_at = :dto.revokedAt
        WHERE id = :dto.id
    """)
    fun update(dto: ConnectionLinkDto)
}

data class ConnectionLinkDto(
    val id: UUID,
    val workspaceId: UUID,
    val token: String,
    val createdBy: UUID?,
    val expiresAt: Instant,
    val revokedAt: Instant?,
    val createdAt: Instant,
)

@RegisterKotlinMapper(ConnectionLinkUsageDto::class)
interface ConnectionLinkUsageDao {
    @SqlQuery("SELECT * FROM onboarding_connection_link_usage WHERE connection_link_id = :connectionLinkId")
    fun findByConnectionLinkId(connectionLinkId: UUID): List<ConnectionLinkUsageDto>

    @SqlUpdate("""
        INSERT INTO onboarding_connection_link_usage (id, connection_link_id, social_account_id, connected_at)
        VALUES (:dto.id, :dto.connectionLinkId, :dto.socialAccountId, :dto.connectedAt)
    """)
    fun insert(dto: ConnectionLinkUsageDto)
}

data class ConnectionLinkUsageDto(
    val id: UUID,
    val connectionLinkId: UUID,
    val socialAccountId: UUID,
    val connectedAt: Instant,
)

@RegisterKotlinMapper(OnboardingChecklistDto::class)
interface OnboardingChecklistDao {
    @SqlQuery("SELECT * FROM onboarding_checklist WHERE user_id = :userId AND workspace_id = :workspaceId")
    fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): OnboardingChecklistDto?

    @SqlUpdate("""
        INSERT INTO onboarding_checklist (id, user_id, workspace_id, is_dismissed, dismissed_at)
        VALUES (:dto.id, :dto.userId, :dto.workspaceId, :dto.isDismissed, :dto.dismissedAt)
    """)
    fun insert(dto: OnboardingChecklistDto)

    @SqlUpdate("""
        UPDATE onboarding_checklist SET is_dismissed = :dto.isDismissed, dismissed_at = :dto.dismissedAt
        WHERE id = :dto.id
    """)
    fun update(dto: OnboardingChecklistDto)
}

data class OnboardingChecklistDto(
    val id: UUID,
    val userId: UUID,
    val workspaceId: UUID,
    val isDismissed: Boolean,
    val dismissedAt: Instant?,
)

@RegisterKotlinMapper(ApiKeyDto::class)
interface ApiKeyDao {
    @SqlQuery("SELECT * FROM api_keys_api_key WHERE id = :id")
    fun findById(id: UUID): ApiKeyDto?

    @SqlQuery("SELECT * FROM api_keys_api_key WHERE lookup_prefix = :lookupPrefix")
    fun findByLookupPrefix(lookupPrefix: String): ApiKeyDto?

    @SqlQuery("SELECT * FROM api_keys_api_key WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<ApiKeyDto>

    @SqlQuery("SELECT * FROM api_keys_api_key WHERE lookup_prefix = :lookupPrefix AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW())")
    fun findActiveByLookupPrefix(lookupPrefix: String): ApiKeyDto?

    @SqlUpdate("""
        INSERT INTO api_keys_api_key (id, workspace_id, name, lookup_prefix, token_hash, permissions, social_account_ids, issued_by, expires_at, revoked_at, last_used_at, last_used_ip, rate_override_writes, rate_override_reads, created_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.lookupPrefix, :dto.tokenHash, :dto.permissions, :dto.socialAccountIds, :dto.issuedBy, :dto.expiresAt, :dto.revokedAt, :dto.lastUsedAt, :dto.lastUsedIp, :dto.rateOverrideWrites, :dto.rateOverrideReads, :dto.createdAt)
    """)
    fun insert(dto: ApiKeyDto)

    @SqlUpdate("""
        UPDATE api_keys_api_key SET revoked_at = :dto.revokedAt, last_used_at = :dto.lastUsedAt, last_used_ip = :dto.lastUsedIp
        WHERE id = :dto.id
    """)
    fun update(dto: ApiKeyDto)
}

data class ApiKeyDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val lookupPrefix: String,
    val tokenHash: String,
    val permissions: String,
    val socialAccountIds: String,
    val issuedBy: UUID?,
    val expiresAt: Instant?,
    val revokedAt: Instant?,
    val lastUsedAt: Instant?,
    val lastUsedIp: String?,
    val rateOverrideWrites: Int?,
    val rateOverrideReads: Int?,
    val createdAt: Instant,
)

@RegisterKotlinMapper(ApiKeyAuditLogDto::class)
interface ApiKeyAuditLogDao {
    @SqlQuery("SELECT * FROM api_keys_audit_log WHERE api_key_id = :apiKeyId ORDER BY created_at DESC")
    fun findByApiKeyId(apiKeyId: UUID): List<ApiKeyAuditLogDto>

    @SqlUpdate("""
        INSERT INTO api_keys_audit_log (id, api_key_id, action, target_id, method, path, status_code, ip, user_agent, created_at)
        VALUES (:dto.id, :dto.apiKeyId, :dto.action, :dto.targetId, :dto.method, :dto.path, :dto.statusCode, :dto.ip, :dto.userAgent, :dto.createdAt)
    """)
    fun insert(dto: ApiKeyAuditLogDto)
}

data class ApiKeyAuditLogDto(
    val id: UUID,
    val apiKeyId: UUID,
    val action: String,
    val targetId: UUID?,
    val method: String,
    val path: String,
    val statusCode: Int,
    val ip: String?,
    val userAgent: String,
    val createdAt: Instant,
)
