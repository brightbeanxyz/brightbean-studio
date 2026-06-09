package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(IdeaMediaDto::class)
interface IdeaMediaDao {
    @SqlQuery("SELECT * FROM composer_idea_media WHERE idea_id = :ideaId ORDER BY position")
    fun findByIdeaId(ideaId: UUID): List<IdeaMediaDto>

    @SqlUpdate("""
        INSERT INTO composer_idea_media (id, idea_id, media_asset_id, position, created_at, updated_at)
        VALUES (:dto.id, :dto.ideaId, :dto.mediaAssetId, :dto.position, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: IdeaMediaDto)

    @SqlUpdate("DELETE FROM composer_idea_media WHERE idea_id = :ideaId")
    fun deleteByIdeaId(ideaId: UUID)

    @SqlUpdate("DELETE FROM composer_idea_media WHERE id = :id")
    fun delete(id: UUID)
}

data class IdeaMediaDto(
    val id: UUID,
    val ideaId: UUID,
    val mediaAssetId: UUID,
    val position: Int,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
