package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PostMedia
import com.brightbean.studio.domain.repository.PostMediaRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPostMediaRepository(jdbi: Jdbi) : PostMediaRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PostMediaDao by lazy { jdbi.onDemand(PostMediaDao::class.java) }

    override fun findByPostId(postId: UUID): List<PostMedia> =
        dao.findByPostId(postId).map { it.toDomain() }

    override fun save(media: PostMedia): PostMedia {
        dao.insert(media.toDto())
        return media
    }

    override fun delete(id: UUID) = dao.delete(id)

    override fun deleteByPostId(postId: UUID) = dao.deleteByPostId(postId)

    private fun PostMedia.toDto() = PostMediaDto(
        id = id, postId = postId, mediaAssetId = mediaAssetId, position = position,
        altText = altText, platformOverrides = platformOverrides ?: "{}",
    )

    private fun PostMediaDto.toDomain() = PostMedia(
        id = id, postId = postId, mediaAssetId = mediaAssetId, position = position,
        altText = altText, platformOverrides = platformOverrides,
    )
}
