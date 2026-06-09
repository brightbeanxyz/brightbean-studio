package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.repository.PostRepository
import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
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
        title = title,
        caption = caption,
        firstComment = firstComment,
        internalNotes = internalNotes,
        tags = objectMapper.writeValueAsString(tags),
        categoryId = categoryId,
        scheduledAt = scheduledAt,
        publishedAt = publishedAt,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun PostDto.toDomain(): Post {
        val tagList: List<String> = try {
            objectMapper.readValue(tags, object : TypeReference<List<String>>() {})
        } catch (_: Exception) {
            emptyList()
        }
        return Post(
            id = id,
            workspaceId = workspaceId,
            authorId = authorId,
            title = title,
            caption = caption,
            firstComment = firstComment,
            internalNotes = internalNotes,
            tags = tagList,
            categoryId = categoryId,
            scheduledAt = scheduledAt,
            publishedAt = publishedAt,
            createdAt = createdAt,
            updatedAt = updatedAt,
        )
    }
}
