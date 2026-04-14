package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(MediaItemDto::class)
interface MediaItemDao {
    @SqlQuery("SELECT * FROM media_item WHERE id = :id")
    fun findById(id: UUID): MediaItemDto?

    @SqlQuery("SELECT * FROM media_item WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<MediaItemDto>

    @SqlUpdate("INSERT INTO media_item (id, workspace_id, storage_type, storage_path, mime_type, size, created_at) VALUES (:dto.id, :dto.workspaceId, :dto.storageType, :dto.storagePath, :dto.mimeType, :dto.size, :dto.createdAt)")
    fun insert(dto: MediaItemDto)

    @SqlUpdate("DELETE FROM media_item WHERE id = :id")
    fun delete(id: UUID)
}

data class MediaItemDto(
    val id: UUID,
    val workspaceId: UUID,
    val storageType: String,
    val storagePath: String,
    val mimeType: String,
    val size: Long,
    val createdAt: java.time.Instant
)