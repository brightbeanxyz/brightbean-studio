package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.MediaAsset
import com.brightbean.studio.domain.model.MediaAssetVersion
import com.brightbean.studio.domain.model.MediaFolder
import com.brightbean.studio.domain.model.MediaType
import com.brightbean.studio.domain.model.ProcessingStatus
import com.brightbean.studio.domain.repository.MediaAssetRepository
import com.brightbean.studio.domain.repository.MediaAssetVersionRepository
import com.brightbean.studio.domain.repository.MediaFolderRepository
import java.time.Instant
import java.util.UUID

class MediaLibraryUseCases(
    private val assetRepository: MediaAssetRepository,
    private val folderRepository: MediaFolderRepository,
    private val versionRepository: MediaAssetVersionRepository,
) {

    fun listAssets(
        workspaceId: UUID,
        folderId: UUID? = null,
        mediaType: MediaType? = null,
        starredOnly: Boolean = false,
        query: String? = null,
    ): List<MediaAsset> {
        if (!query.isNullOrBlank()) {
            return assetRepository.search(workspaceId, query)
        }
        if (starredOnly) {
            return assetRepository.findStarred(workspaceId)
        }
        if (mediaType != null) {
            return assetRepository.findByMediaType(workspaceId, mediaType)
        }
        if (folderId != null) {
            return assetRepository.findByFolderId(folderId)
        }
        return assetRepository.findByWorkspaceId(workspaceId)
    }

    fun uploadAsset(
        workspaceId: UUID,
        filename: String,
        mediaType: MediaType,
        mimeType: String,
        fileSize: Long,
        filePath: String,
        uploadedBy: UUID?,
        organizationId: UUID? = null,
        folderId: UUID? = null,
        width: Int = 0,
        height: Int = 0,
        duration: Double = 0.0,
        thumbnailPath: String = "",
        altText: String = "",
        title: String = "",
        tags: List<String> = emptyList(),
        source: String = "",
        sourceUrl: String = "",
        attribution: String = "",
    ): MediaAsset {
        val now = Instant.now()
        val asset = MediaAsset(
            id = UUID.randomUUID(),
            organizationId = organizationId,
            workspaceId = workspaceId,
            folderId = folderId,
            uploadedBy = uploadedBy,
            filename = filename,
            mediaType = mediaType,
            mimeType = mimeType,
            fileSize = fileSize,
            width = width,
            height = height,
            duration = duration,
            filePath = filePath,
            thumbnailPath = thumbnailPath,
            altText = altText,
            title = title,
            tags = tags,
            isStarred = false,
            source = source,
            sourceUrl = sourceUrl,
            attribution = attribution,
            processingStatus = ProcessingStatus.COMPLETED,
            processedVariants = null,
            currentVersionId = null,
            createdAt = now,
            updatedAt = now,
        )
        return assetRepository.save(asset)
    }

    fun updateAsset(id: UUID, altText: String? = null, title: String? = null, tags: List<String>? = null): MediaAsset {
        val asset = assetRepository.findById(id)
            ?: throw IllegalArgumentException("Asset not found: $id")
        val updated = asset.copy(
            altText = altText ?: asset.altText,
            title = title ?: asset.title,
            tags = tags ?: asset.tags,
            updatedAt = Instant.now(),
        )
        return assetRepository.update(updated)
    }

    fun starAsset(id: UUID): MediaAsset {
        val asset = assetRepository.findById(id)
            ?: throw IllegalArgumentException("Asset not found: $id")
        val updated = asset.copy(
            isStarred = !asset.isStarred,
            updatedAt = Instant.now(),
        )
        return assetRepository.update(updated)
    }

    fun moveAsset(id: UUID, folderId: UUID?): MediaAsset {
        val asset = assetRepository.findById(id)
            ?: throw IllegalArgumentException("Asset not found: $id")
        val updated = asset.copy(
            folderId = folderId,
            updatedAt = Instant.now(),
        )
        return assetRepository.update(updated)
    }

    fun deleteAsset(id: UUID) {
        assetRepository.delete(id)
    }

    fun listFolders(workspaceId: UUID): List<MediaFolder> =
        folderRepository.findByWorkspaceId(workspaceId)

    fun createFolder(workspaceId: UUID, name: String, parentFolderId: UUID? = null, organizationId: UUID? = null): MediaFolder {
        if (parentFolderId != null) {
            val depth = calculateFolderDepth(parentFolderId)
            if (depth >= 2) {
                throw IllegalArgumentException("Maximum folder nesting depth of 3 levels exceeded")
            }
        }
        val now = Instant.now()
        val folder = MediaFolder(
            id = UUID.randomUUID(),
            organizationId = organizationId ?: UUID.randomUUID(),
            workspaceId = workspaceId,
            parentFolderId = parentFolderId,
            name = name,
            createdAt = now,
            updatedAt = now,
        )
        return folderRepository.save(folder)
    }

    fun renameFolder(id: UUID, name: String): MediaFolder {
        val folder = folderRepository.findById(id)
            ?: throw IllegalArgumentException("Folder not found: $id")
        val updated = folder.copy(
            name = name,
            updatedAt = Instant.now(),
        )
        return folderRepository.update(updated)
    }

    fun deleteFolder(id: UUID) {
        val folder = folderRepository.findById(id) ?: return
        val assets = assetRepository.findByFolderId(id)
        for (asset in assets) {
            assetRepository.update(asset.copy(folderId = folder.parentFolderId, updatedAt = Instant.now()))
        }
        val subFolders = folderRepository.findByParentFolderId(id)
        for (sub in subFolders) {
            folderRepository.update(sub.copy(parentFolderId = folder.parentFolderId, updatedAt = Instant.now()))
        }
        folderRepository.delete(id)
    }

    fun listVersions(assetId: UUID): List<MediaAssetVersion> =
        versionRepository.findByMediaAssetId(assetId)

    fun createVersion(assetId: UUID, filePath: String, changeDescription: String, createdBy: UUID?): MediaAssetVersion {
        val asset = assetRepository.findById(assetId)
            ?: throw IllegalArgumentException("Asset not found: $assetId")
        val latest = versionRepository.findLatestByMediaAssetId(assetId)
        val nextVersion = (latest?.versionNumber ?: 0) + 1
        val version = MediaAssetVersion(
            id = UUID.randomUUID(),
            mediaAssetId = assetId,
            versionNumber = nextVersion,
            filePath = filePath,
            thumbnailPath = asset.thumbnailPath,
            changeDescription = changeDescription,
            fileSize = asset.fileSize,
            width = asset.width,
            height = asset.height,
            duration = asset.duration,
            createdBy = createdBy,
            createdAt = Instant.now(),
        )
        val saved = versionRepository.save(version)
        assetRepository.update(asset.copy(currentVersionId = saved.id, updatedAt = Instant.now()))
        return saved
    }

    private fun calculateFolderDepth(folderId: UUID): Int {
        var depth = 0
        var currentId: UUID? = folderId
        while (currentId != null) {
            val folder = folderRepository.findById(currentId) ?: break
            depth++
            currentId = folder.parentFolderId
        }
        return depth
    }
}
