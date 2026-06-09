package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(FeedDto::class)
interface FeedDao {
    @SqlQuery("SELECT * FROM composer_feed WHERE id = :id")
    fun findById(id: UUID): FeedDto?

    @SqlQuery("SELECT * FROM composer_feed WHERE workspace_id = :workspaceId ORDER BY name")
    fun findByWorkspaceId(workspaceId: UUID): List<FeedDto>

    @SqlUpdate("""
        INSERT INTO composer_feed (id, workspace_id, name, url, website_url, added_by, created_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.url, :dto.websiteUrl, :dto.addedBy, :dto.createdAt)
    """)
    fun insert(dto: FeedDto)

    @SqlUpdate("DELETE FROM composer_feed WHERE id = :id")
    fun delete(id: UUID)
}

data class FeedDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val url: String,
    val websiteUrl: String,
    val addedBy: UUID?,
    val createdAt: java.time.Instant,
)
