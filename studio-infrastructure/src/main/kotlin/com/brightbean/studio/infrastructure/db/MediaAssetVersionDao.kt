package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(MediaAssetVersionDto::class)
interface MediaAssetVersionDao {
    @SqlQuery("SELECT * FROM media_library_asset_version WHERE media_asset_id = :mediaAssetId ORDER BY version_number DESC")
    fun findByMediaAssetId(mediaAssetId: UUID): List<MediaAssetVersionDto>

    @SqlQuery("SELECT * FROM media_library_asset_version WHERE media_asset_id = :mediaAssetId ORDER BY version_number DESC LIMIT 1")
    fun findLatestByMediaAssetId(mediaAssetId: UUID): MediaAssetVersionDto?

    @SqlUpdate("""
        INSERT INTO media_library_asset_version (id, media_asset_id, version_number, file_path, thumbnail_path, change_description, file_size, width, height, duration, created_by, created_at)
        VALUES (:dto.id, :dto.mediaAssetId, :dto.versionNumber, :dto.filePath, :dto.thumbnailPath, :dto.changeDescription, :dto.fileSize, :dto.width, :dto.height, :dto.duration, :dto.createdBy, :dto.createdAt)
    """)
    fun insert(dto: MediaAssetVersionDto)
}

data class MediaAssetVersionDto(
    val id: UUID,
    val mediaAssetId: UUID,
    val versionNumber: Int,
    val filePath: String,
    val thumbnailPath: String,
    val changeDescription: String,
    val fileSize: Long,
    val width: Int?,
    val height: Int?,
    val duration: Double?,
    val createdBy: UUID?,
    val createdAt: java.time.Instant,
)
