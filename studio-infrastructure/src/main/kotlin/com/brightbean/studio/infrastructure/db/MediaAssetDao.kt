package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(MediaAssetDto::class)
interface MediaAssetDao {
    @SqlQuery("SELECT * FROM media_library_media_asset WHERE id = :id")
    fun findById(id: UUID): MediaAssetDto?

    @SqlQuery("SELECT * FROM media_library_media_asset WHERE workspace_id = :workspaceId ORDER BY created_at DESC")
    fun findByWorkspaceId(workspaceId: UUID): List<MediaAssetDto>

    @SqlQuery("SELECT * FROM media_library_media_asset WHERE folder_id IS NOT DISTINCT FROM :folderId ORDER BY created_at DESC")
    fun findByFolderId(folderId: UUID?): List<MediaAssetDto>

    @SqlQuery("SELECT * FROM media_library_media_asset WHERE workspace_id = :workspaceId AND is_starred = true ORDER BY created_at DESC")
    fun findStarred(workspaceId: UUID): List<MediaAssetDto>

    @SqlQuery("SELECT * FROM media_library_media_asset WHERE workspace_id = :workspaceId AND media_type = :mediaType ORDER BY created_at DESC")
    fun findByMediaType(workspaceId: UUID, mediaType: String): List<MediaAssetDto>

    @SqlQuery("SELECT * FROM media_library_media_asset WHERE workspace_id = :workspaceId AND (filename ILIKE :query OR title ILIKE :query OR alt_text ILIKE :query) ORDER BY created_at DESC")
    fun search(workspaceId: UUID, query: String): List<MediaAssetDto>

    @SqlUpdate("""
        INSERT INTO media_library_media_asset (id, organization_id, workspace_id, folder_id, uploaded_by, filename, media_type, mime_type, file_size, width, height, duration, file_path, thumbnail_path, alt_text, title, tags, is_starred, source, source_url, attribution, processing_status, processed_variants, current_version_id, created_at, updated_at)
        VALUES (:dto.id, :dto.organizationId, :dto.workspaceId, :dto.folderId, :dto.uploadedBy, :dto.filename, :dto.mediaType, :dto.mimeType, :dto.fileSize, :dto.width, :dto.height, :dto.duration, :dto.filePath, :dto.thumbnailPath, :dto.altText, :dto.title, :dto.tags, :dto.isStarred, :dto.source, :dto.sourceUrl, :dto.attribution, :dto.processingStatus, :dto.processedVariants, :dto.currentVersionId, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: MediaAssetDto)

    @SqlUpdate("""
        UPDATE media_library_media_asset SET
            folder_id = :dto.folderId,
            filename = :dto.filename,
            alt_text = :dto.altText,
            title = :dto.title,
            tags = :dto.tags,
            is_starred = :dto.isStarred,
            processing_status = :dto.processingStatus,
            processed_variants = :dto.processedVariants,
            current_version_id = :dto.currentVersionId,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: MediaAssetDto)

    @SqlUpdate("DELETE FROM media_library_media_asset WHERE id = :id")
    fun delete(id: UUID)
}

data class MediaAssetDto(
    val id: UUID,
    val organizationId: UUID?,
    val workspaceId: UUID?,
    val folderId: UUID?,
    val uploadedBy: UUID?,
    val filename: String,
    val mediaType: String,
    val mimeType: String,
    val fileSize: Long,
    val width: Int,
    val height: Int,
    val duration: Double,
    val filePath: String,
    val thumbnailPath: String,
    val altText: String,
    val title: String,
    val tags: String,
    val isStarred: Boolean,
    val source: String,
    val sourceUrl: String,
    val attribution: String,
    val processingStatus: String,
    val processedVariants: String?,
    val currentVersionId: UUID?,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
