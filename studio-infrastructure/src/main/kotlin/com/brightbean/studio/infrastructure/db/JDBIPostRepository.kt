package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.Tag
import com.brightbean.studio.domain.repository.PostRepository
import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.time.Instant
import java.util.UUID

class JDBIPostRepository(jdbi: Jdbi) : PostRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PostDao by lazy { jdbi.onDemand(PostDao::class.java) }

    override fun findById(id: UUID): Post? =
        dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Post> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByAuthorId(authorId: UUID): List<Post> =
        dao.findByAuthorId(authorId).map { it.toDomain() }

    override fun save(post: Post): Post {
        dao.insert(post.toDto())
        return post
    }

    override fun update(post: Post): Post {
        dao.update(post.toDto())
        return post
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun Post.toDto() = PostDto(
        id = id,
        workspaceId = workspaceId,
        authorId = authorId,
        content = content,
        platforms = objectMapper.writeValueAsString(platforms.map { it.name }),
        categoryId = categoryId,
        tags = objectMapper.writeValueAsString(tags.map { it.name }),
        status = status.name,
        scheduledAt = scheduledAt,
        publishedAt = publishedAt,
        mediaIds = objectMapper.writeValueAsString(mediaIds),
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun PostDto.toDomain(): Post {
        val platformList: List<PlatformType> = try {
            objectMapper.readValue(platforms, object : TypeReference<List<String>>() {}).map { PlatformType.valueOf(it) }
        } catch (_: Exception) {
            emptyList()
        }
        val tagList: List<Tag> = try {
            objectMapper.readValue(tags, object : TypeReference<List<String>>() {}).map { Tag(id = UUID.randomUUID(), workspaceId = UUID.randomUUID(), name = it, createdAt = Instant.now()) }
        } catch (_: Exception) {
            emptyList()
        }
        val mediaIdList: List<UUID> = try {
            objectMapper.readValue(mediaIds, object : TypeReference<List<UUID>>() {})
        } catch (_: Exception) {
            emptyList()
        }
        return Post(
            id = id,
            workspaceId = workspaceId,
            authorId = authorId,
            content = content,
            platforms = platformList,
            categoryId = categoryId,
            tags = tagList,
            status = PostStatus.valueOf(status),
            scheduledAt = scheduledAt,
            publishedAt = publishedAt,
            mediaIds = mediaIdList,
            createdAt = createdAt,
            updatedAt = updatedAt,
        )
    }
}
