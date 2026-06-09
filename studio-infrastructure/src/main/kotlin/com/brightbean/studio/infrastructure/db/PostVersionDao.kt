package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(PostVersionDto::class)
interface PostVersionDao {
    @SqlQuery("SELECT * FROM composer_post_version WHERE post_id = :postId ORDER BY version_number DESC")
    fun findByPostId(postId: UUID): List<PostVersionDto>

    @SqlQuery("SELECT * FROM composer_post_version WHERE post_id = :postId ORDER BY version_number DESC LIMIT 1")
    fun findLatestByPostId(postId: UUID): PostVersionDto?

    @SqlUpdate("""
        INSERT INTO composer_post_version (id, post_id, version_number, snapshot, created_by, created_at)
        VALUES (:dto.id, :dto.postId, :dto.versionNumber, :dto.snapshot, :dto.createdBy, :dto.createdAt)
    """)
    fun insert(dto: PostVersionDto)
}

data class PostVersionDto(
    val id: UUID,
    val postId: UUID,
    val versionNumber: Int,
    val snapshot: String,
    val createdBy: UUID?,
    val createdAt: java.time.Instant,
)
