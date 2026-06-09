package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterKotlinMapper(PlatformPostDto::class)
interface PlatformPostDao {
    @SqlQuery("SELECT * FROM composer_platform_post WHERE id = :id")
    fun findById(id: UUID): PlatformPostDto?

    @SqlQuery("SELECT * FROM composer_platform_post WHERE post_id = :postId")
    fun findByPostId(postId: UUID): List<PlatformPostDto>

    @SqlQuery("SELECT * FROM composer_platform_post WHERE social_account_id = :socialAccountId")
    fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPostDto>

    @SqlQuery("SELECT * FROM composer_platform_post WHERE status = :status")
    fun findByStatus(status: String): List<PlatformPostDto>

    @SqlQuery("SELECT * FROM composer_platform_post WHERE status = 'SCHEDULED' AND scheduled_at <= :time")
    fun findScheduledBefore(time: Instant): List<PlatformPostDto>

    @SqlUpdate("""
        INSERT INTO composer_platform_post (id, post_id, social_account_id, platform_specific_title, platform_specific_caption, platform_specific_media, platform_specific_first_comment, platform_extra, status, platform_post_id, publish_error, published_at, scheduled_at, retry_count, next_retry_at, created_at, updated_at)
        VALUES (:dto.id, :dto.postId, :dto.socialAccountId, :dto.platformTitle, :dto.platformCaption, :dto.platformMedia, :dto.platformFirstComment, :dto.platformExtra, :dto.status, :dto.platformPostId, :dto.publishError, :dto.publishedAt, :dto.scheduledAt, :dto.retryCount, :dto.nextRetryAt, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: PlatformPostDto)

    @SqlUpdate("""
        UPDATE composer_platform_post SET
            platform_specific_title = :dto.platformTitle,
            platform_specific_caption = :dto.platformCaption,
            platform_specific_media = :dto.platformMedia,
            platform_specific_first_comment = :dto.platformFirstComment,
            platform_extra = :dto.platformExtra,
            status = :dto.status,
            platform_post_id = :dto.platformPostId,
            publish_error = :dto.publishError,
            published_at = :dto.publishedAt,
            scheduled_at = :dto.scheduledAt,
            retry_count = :dto.retryCount,
            next_retry_at = :dto.nextRetryAt,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PlatformPostDto)

    @SqlUpdate("DELETE FROM composer_platform_post WHERE id = :id")
    fun delete(id: UUID)
}

data class PlatformPostDto(
    val id: UUID,
    val postId: UUID,
    val socialAccountId: UUID,
    val platformTitle: String?,
    val platformCaption: String?,
    val platformMedia: String?,
    val platformFirstComment: String?,
    val platformExtra: String?,
    val status: String,
    val platformPostId: String,
    val publishError: String,
    val publishedAt: Instant?,
    val scheduledAt: Instant?,
    val retryCount: Int,
    val nextRetryAt: Instant?,
    val createdAt: Instant,
    val updatedAt: Instant,
)
