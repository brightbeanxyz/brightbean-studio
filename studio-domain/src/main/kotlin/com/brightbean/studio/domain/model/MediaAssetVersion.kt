package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class MediaAssetVersion(
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
    val createdAt: Instant,
)
