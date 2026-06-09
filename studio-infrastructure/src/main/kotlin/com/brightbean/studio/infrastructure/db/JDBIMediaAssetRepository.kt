package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.MediaAsset
import com.brightbean.studio.domain.model.MediaType
import com.brightbean.studio.domain.model.ProcessingStatus
import com.brightbean.studio.domain.repository.MediaAssetRepository
import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIMediaAssetRepository(jdbi: Jdbi) : MediaAssetRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: MediaAssetDao by lazy { jdbi.onDemand(MediaAssetDao::class.java) }

    override fun findById(id: UUID): MediaAsset? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<MediaAsset> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByFolderId(folderId: UUID?): List<MediaAsset> =
        dao.findByFolderId(folderId).map { it.toDomain() }

    override fun findStarred(workspaceId: UUID): List<MediaAsset> =
        dao.findStarred(workspaceId).map { it.toDomain() }

    override fun findByMediaType(workspaceId: UUID, mediaType: MediaType): List<MediaAsset> =
        dao.findByMediaType(workspaceId, mediaType.name).map { it.toDomain() }

    override fun search(workspaceId: UUID, query: String): List<MediaAsset> =
        dao.search(workspaceId, "%$query%").map { it.toDomain() }

    override fun save(asset: MediaAsset): MediaAsset {
        dao.insert(asset.toDto())
        return asset
    }

    override fun update(asset: MediaAsset): MediaAsset {
        dao.update(asset.toDto())
        return asset
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun MediaAsset.toDto() = MediaAssetDto(
        id = id, organizationId = organizationId, workspaceId = workspaceId,
        folderId = folderId, uploadedBy = uploadedBy, filename = filename,
        mediaType = mediaType.name, mimeType = mimeType, fileSize = fileSize,
        width = width, height = height, duration = duration,
        filePath = filePath, thumbnailPath = thumbnailPath,
        altText = altText, title = title,
        tags = objectMapper.writeValueAsString(tags),
        isStarred = isStarred, source = source, sourceUrl = sourceUrl,
        attribution = attribution, processingStatus = processingStatus.name,
        processedVariants = processedVariants, currentVersionId = currentVersionId,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun MediaAssetDto.toDomain(): MediaAsset {
        val tagList: List<String> = try {
            objectMapper.readValue(tags, object : TypeReference<List<String>>() {})
        } catch (_: Exception) { emptyList() }
        return MediaAsset(
            id = id, organizationId = organizationId, workspaceId = workspaceId,
            folderId = folderId, uploadedBy = uploadedBy, filename = filename,
            mediaType = try { MediaType.valueOf(mediaType) } catch (_: Exception) { MediaType.IMAGE },
            mimeType = mimeType, fileSize = fileSize, width = width, height = height,
            duration = duration, filePath = filePath, thumbnailPath = thumbnailPath,
            altText = altText, title = title, tags = tagList, isStarred = isStarred,
            source = source, sourceUrl = sourceUrl, attribution = attribution,
            processingStatus = try { ProcessingStatus.valueOf(processingStatus) } catch (_: Exception) { ProcessingStatus.COMPLETED },
            processedVariants = processedVariants, currentVersionId = currentVersionId,
            createdAt = createdAt, updatedAt = updatedAt,
        )
    }
}
