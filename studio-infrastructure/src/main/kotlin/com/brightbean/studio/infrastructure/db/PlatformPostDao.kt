package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterBeanMapper(PlatformPostDto::class)
interface PlatformPostDao {
    @SqlQuery("SELECT * FROM platform_post WHERE id = :id")
    fun findById(id: UUID): PlatformPostDto?

    @SqlQuery("SELECT * FROM platform_post WHERE post_id = :postId")
    fun findByPostId(postId: UUID): List<PlatformPostDto>

    @SqlQuery("SELECT * FROM platform_post WHERE social_account_id = :socialAccountId")
    fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPostDto>

    @SqlUpdate("""
        INSERT INTO platform_post (id, post_id, social_account_id, platform_post_id, platform_url, status, error_message, published_at)
        VALUES (:dto.id, :dto.postId, :dto.socialAccountId, :dto.platformPostId, :dto.platformUrl, :dto.status, :dto.errorMessage, :dto.publishedAt)
    """)
    fun insert(dto: PlatformPostDto)

    @SqlUpdate("""
        UPDATE platform_post SET
            platform_post_id = :dto.platformPostId,
            platform_url = :dto.platformUrl,
            status = :dto.status,
            error_message = :dto.errorMessage,
            published_at = :dto.publishedAt
        WHERE id = :dto.id
    """)
    fun update(dto: PlatformPostDto)

    @SqlUpdate("DELETE FROM platform_post WHERE id = :id")
    fun delete(id: UUID)
}

data class PlatformPostDto(
    val id: UUID,
    val postId: UUID,
    val socialAccountId: UUID,
    val platformPostId: String?,
    val platformUrl: String?,
    val status: String,
    val errorMessage: String?,
    val publishedAt: Instant?,
)
