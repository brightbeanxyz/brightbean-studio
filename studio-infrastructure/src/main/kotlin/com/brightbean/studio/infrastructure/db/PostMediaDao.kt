package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(PostMediaDto::class)
interface PostMediaDao {
    @SqlQuery("SELECT * FROM composer_post_media WHERE post_id = :postId ORDER BY position")
    fun findByPostId(postId: UUID): List<PostMediaDto>

    @SqlUpdate("""
        INSERT INTO composer_post_media (id, post_id, media_asset_id, position, alt_text, platform_overrides)
        VALUES (:dto.id, :dto.postId, :dto.mediaAssetId, :dto.position, :dto.altText, :dto.platformOverrides)
    """)
    fun insert(dto: PostMediaDto)

    @SqlUpdate("DELETE FROM composer_post_media WHERE id = :id")
    fun delete(id: UUID)

    @SqlUpdate("DELETE FROM composer_post_media WHERE post_id = :postId")
    fun deleteByPostId(postId: UUID)
}

data class PostMediaDto(
    val id: UUID,
    val postId: UUID,
    val mediaAssetId: UUID,
    val position: Int,
    val altText: String,
    val platformOverrides: String,
)
