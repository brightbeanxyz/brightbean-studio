package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPlatformPostRepository(jdbi: Jdbi) : PlatformPostRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PlatformPostDao by lazy { jdbi.onDemand(PlatformPostDao::class.java) }

    override fun findById(id: UUID): PlatformPost? =
        dao.findById(id)?.toDomain()

    override fun findByPostId(postId: UUID): List<PlatformPost> =
        dao.findByPostId(postId).map { it.toDomain() }

    override fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost> =
        dao.findBySocialAccountId(socialAccountId).map { it.toDomain() }

    override fun save(platformPost: PlatformPost): PlatformPost {
        dao.insert(platformPost.toDto())
        return platformPost
    }

    override fun update(platformPost: PlatformPost): PlatformPost {
        dao.update(platformPost.toDto())
        return platformPost
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun PlatformPost.toDto() = PlatformPostDto(
        id = id,
        postId = postId,
        socialAccountId = socialAccountId,
        platformPostId = platformPostId,
        platformUrl = platformUrl,
        status = status.name,
        errorMessage = errorMessage,
        publishedAt = publishedAt,
    )

    private fun PlatformPostDto.toDomain() = PlatformPost(
        id = id,
        postId = postId,
        socialAccountId = socialAccountId,
        platformPostId = platformPostId,
        platformUrl = platformUrl,
        status = PostStatus.valueOf(status),
        errorMessage = errorMessage,
        publishedAt = publishedAt,
    )
}
