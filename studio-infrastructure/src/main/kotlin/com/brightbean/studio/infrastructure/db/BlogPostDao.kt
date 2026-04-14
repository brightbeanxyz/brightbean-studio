package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterBeanMapper(BlogPostDto::class)
interface BlogPostDao {
    @SqlQuery("SELECT * FROM blog_post WHERE id = :id")
    fun findById(id: UUID): BlogPostDto?

    @SqlQuery("SELECT * FROM blog_post WHERE slug = :slug")
    fun findBySlug(slug: String): BlogPostDto?

    @SqlQuery("SELECT * FROM blog_post WHERE published_at IS NOT NULL ORDER BY published_at DESC")
    fun findAllPublished(): List<BlogPostDto>

    @SqlQuery("SELECT * FROM blog_post ORDER BY created_at DESC")
    fun findAll(): List<BlogPostDto>

    @SqlUpdate("""
        INSERT INTO blog_post (id, title, content, excerpt, slug, author_id, tags, published_at, created_at, updated_at)
        VALUES (:dto.id, :dto.title, :dto.content, :dto.excerpt, :dto.slug, :dto.authorId, :dto.tags, :dto.publishedAt, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: BlogPostDto)

    @SqlUpdate("""
        UPDATE blog_post SET
            title = :dto.title,
            content = :dto.content,
            excerpt = :dto.excerpt,
            slug = :dto.slug,
            tags = :dto.tags,
            published_at = :dto.publishedAt,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: BlogPostDto)

    @SqlUpdate("DELETE FROM blog_post WHERE id = :id")
    fun delete(id: UUID)
}

data class BlogPostDto(
    val id: UUID,
    val title: String,
    val content: String,
    val excerpt: String,
    val slug: String,
    val authorId: UUID,
    val tags: String,
    val publishedAt: java.time.Instant?,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
