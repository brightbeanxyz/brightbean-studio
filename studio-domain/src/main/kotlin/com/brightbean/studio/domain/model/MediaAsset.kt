package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

enum class MediaType { IMAGE, VIDEO, GIF, DOCUMENT }
enum class ProcessingStatus { PENDING, PROCESSING, COMPLETED, FAILED }

data class MediaAsset(
    val id: UUID,
    val organizationId: UUID?,
    val workspaceId: UUID?,
    val folderId: UUID?,
    val uploadedBy: UUID?,
    val filename: String,
    val mediaType: MediaType,
    val mimeType: String,
    val fileSize: Long,
    val width: Int,
    val height: Int,
    val duration: Double,
    val filePath: String,
    val thumbnailPath: String,
    val altText: String,
    val title: String,
    val tags: List<String>,
    val isStarred: Boolean,
    val source: String,
    val sourceUrl: String,
    val attribution: String,
    val processingStatus: ProcessingStatus,
    val processedVariants: String?,
    val currentVersionId: UUID?,
    val createdAt: Instant,
    val updatedAt: Instant,
) {
    val isImage: Boolean get() = mediaType == MediaType.IMAGE
    val isVideo: Boolean get() = mediaType == MediaType.VIDEO
    val aspectRatio: Double get() = if (height > 0) (width.toDouble() / height.toDouble()).coerceIn(0.0, 10.0).let { Math.round(it * 100.0) / 100.0 } else 0.0
}
