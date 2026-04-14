package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterBeanMapper(StaticPageDto::class)
interface StaticPageDao {
    @SqlQuery("SELECT * FROM static_page WHERE id = :id")
    fun findById(id: UUID): StaticPageDto?

    @SqlQuery("SELECT * FROM static_page WHERE slug = :slug")
    fun findBySlug(slug: String): StaticPageDto?

    @SqlQuery("SELECT * FROM static_page ORDER BY updated_at DESC")
    fun findAll(): List<StaticPageDto>

    @SqlUpdate("""
        INSERT INTO static_page (id, title, content, slug, created_at, updated_at)
        VALUES (:dto.id, :dto.title, :dto.content, :dto.slug, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: StaticPageDto)

    @SqlUpdate("""
        UPDATE static_page SET
            title = :dto.title,
            content = :dto.content,
            slug = :dto.slug,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: StaticPageDto)

    @SqlUpdate("DELETE FROM static_page WHERE id = :id")
    fun delete(id: UUID)
}

data class StaticPageDto(
    val id: UUID,
    val title: String,
    val content: String,
    val slug: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
