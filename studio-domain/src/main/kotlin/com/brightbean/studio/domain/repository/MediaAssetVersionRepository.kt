package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.MediaAssetVersion
import java.util.UUID

interface MediaAssetVersionRepository {
    fun findByMediaAssetId(mediaAssetId: UUID): List<MediaAssetVersion>
    fun findLatestByMediaAssetId(mediaAssetId: UUID): MediaAssetVersion?
    fun save(version: MediaAssetVersion): MediaAssetVersion
}
