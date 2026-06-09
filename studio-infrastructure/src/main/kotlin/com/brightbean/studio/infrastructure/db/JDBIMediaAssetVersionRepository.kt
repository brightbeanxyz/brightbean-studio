package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.MediaAssetVersion
import com.brightbean.studio.domain.repository.MediaAssetVersionRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIMediaAssetVersionRepository(jdbi: Jdbi) : MediaAssetVersionRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: MediaAssetVersionDao by lazy { jdbi.onDemand(MediaAssetVersionDao::class.java) }

    override fun findByMediaAssetId(mediaAssetId: UUID): List<MediaAssetVersion> =
        dao.findByMediaAssetId(mediaAssetId).map { it.toDomain() }

    override fun findLatestByMediaAssetId(mediaAssetId: UUID): MediaAssetVersion? =
        dao.findLatestByMediaAssetId(mediaAssetId)?.toDomain()

    override fun save(version: MediaAssetVersion): MediaAssetVersion {
        dao.insert(version.toDto())
        return version
    }

    private fun MediaAssetVersion.toDto() = MediaAssetVersionDto(
        id = id, mediaAssetId = mediaAssetId, versionNumber = versionNumber,
        filePath = filePath, thumbnailPath = thumbnailPath,
        changeDescription = changeDescription, fileSize = fileSize,
        width = width, height = height, duration = duration,
        createdBy = createdBy, createdAt = createdAt,
    )

    private fun MediaAssetVersionDto.toDomain() = MediaAssetVersion(
        id = id, mediaAssetId = mediaAssetId, versionNumber = versionNumber,
        filePath = filePath, thumbnailPath = thumbnailPath,
        changeDescription = changeDescription, fileSize = fileSize,
        width = width, height = height, duration = duration,
        createdBy = createdBy, createdAt = createdAt,
    )
}
