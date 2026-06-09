package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PostVersion
import com.brightbean.studio.domain.repository.PostVersionRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPostVersionRepository(jdbi: Jdbi) : PostVersionRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PostVersionDao by lazy { jdbi.onDemand(PostVersionDao::class.java) }

    override fun findByPostId(postId: UUID): List<PostVersion> =
        dao.findByPostId(postId).map { it.toDomain() }

    override fun findLatestByPostId(postId: UUID): PostVersion? =
        dao.findLatestByPostId(postId)?.toDomain()

    override fun save(version: PostVersion): PostVersion {
        dao.insert(version.toDto())
        return version
    }

    private fun PostVersion.toDto() = PostVersionDto(
        id = id, postId = postId, versionNumber = versionNumber,
        snapshot = snapshot, createdBy = createdBy, createdAt = createdAt,
    )

    private fun PostVersionDto.toDomain() = PostVersion(
        id = id, postId = postId, versionNumber = versionNumber,
        snapshot = snapshot, createdBy = createdBy, createdAt = createdAt,
    )
}
