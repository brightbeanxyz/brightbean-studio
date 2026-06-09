package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.MediaAsset
import com.brightbean.studio.domain.model.MediaAssetVersion
import com.brightbean.studio.domain.model.MediaFolder
import com.brightbean.studio.domain.model.MediaType
import com.brightbean.studio.domain.model.ProcessingStatus
import com.brightbean.studio.domain.repository.MediaAssetRepository
import com.brightbean.studio.domain.repository.MediaAssetVersionRepository
import com.brightbean.studio.domain.repository.MediaFolderRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class MediaLibraryUseCasesTest {

    private lateinit var assetRepository: MediaAssetInMemoryRepository
    private lateinit var folderRepository: MediaFolderInMemoryRepository
    private lateinit var versionRepository: MediaAssetVersionInMemoryRepository
    private lateinit var useCases: MediaLibraryUseCases

    @BeforeEach
    fun setUp() {
        assetRepository = MediaAssetInMemoryRepository()
        folderRepository = MediaFolderInMemoryRepository()
        versionRepository = MediaAssetVersionInMemoryRepository()
        useCases = MediaLibraryUseCases(assetRepository, folderRepository, versionRepository)
    }

    @Test
    fun `list assets returns all workspace assets`() {
        val workspaceId = UUID.randomUUID()
        assetRepository.save(testAsset(workspaceId = workspaceId, filename = "a.png"))
        assetRepository.save(testAsset(workspaceId = workspaceId, filename = "b.jpg"))
        assetRepository.save(testAsset(workspaceId = UUID.randomUUID(), filename = "c.gif"))

        val assets = useCases.listAssets(workspaceId)
        assertEquals(2, assets.size)
    }

    @Test
    fun `upload asset creates and returns asset`() {
        val workspaceId = UUID.randomUUID()
        val asset = useCases.uploadAsset(
            workspaceId = workspaceId,
            filename = "photo.jpg",
            mediaType = MediaType.IMAGE,
            mimeType = "image/jpeg",
            fileSize = 1024,
            filePath = "/uploads/photo.jpg",
            uploadedBy = UUID.randomUUID(),
        )

        assertNotNull(asset.id)
        assertEquals("photo.jpg", asset.filename)
        assertEquals(MediaType.IMAGE, asset.mediaType)
        assertFalse(asset.isStarred)
        assertEquals(0.0, asset.aspectRatio)
    }

    @Test
    fun `star asset toggles starred status`() {
        val workspaceId = UUID.randomUUID()
        val created = assetRepository.save(testAsset(workspaceId = workspaceId))
        assertFalse(created.isStarred)

        val starred = useCases.starAsset(created.id)
        assertTrue(starred.isStarred)

        val unstarred = useCases.starAsset(created.id)
        assertFalse(unstarred.isStarred)
    }

    @Test
    fun `move asset updates folder`() {
        val workspaceId = UUID.randomUUID()
        val created = assetRepository.save(testAsset(workspaceId = workspaceId))
        val folderId = UUID.randomUUID()

        val moved = useCases.moveAsset(created.id, folderId)
        assertEquals(folderId, moved.folderId)
    }

    @Test
    fun `folder CRUD operations`() {
        val workspaceId = UUID.randomUUID()

        val folder = useCases.createFolder(workspaceId, "Images")
        assertNotNull(folder.id)
        assertEquals("Images", folder.name)

        val folders = useCases.listFolders(workspaceId)
        assertEquals(1, folders.size)

        val renamed = useCases.renameFolder(folder.id, "Photos")
        assertEquals("Photos", renamed.name)

        useCases.deleteFolder(folder.id)
        assertTrue(useCases.listFolders(workspaceId).isEmpty())
    }
}

private fun testAsset(
    workspaceId: UUID,
    filename: String = "test.png",
    mediaType: MediaType = MediaType.IMAGE,
) = MediaAsset(
    id = UUID.randomUUID(),
    organizationId = null,
    workspaceId = workspaceId,
    folderId = null,
    uploadedBy = null,
    filename = filename,
    mediaType = mediaType,
    mimeType = "image/png",
    fileSize = 100L,
    width = 0,
    height = 0,
    duration = 0.0,
    filePath = "/uploads/$filename",
    thumbnailPath = "",
    altText = "",
    title = "",
    tags = emptyList(),
    isStarred = false,
    source = "",
    sourceUrl = "",
    attribution = "",
    processingStatus = ProcessingStatus.COMPLETED,
    processedVariants = null,
    currentVersionId = null,
    createdAt = Instant.now(),
    updatedAt = Instant.now(),
)

class MediaAssetInMemoryRepository : MediaAssetRepository {
    private val assets = mutableMapOf<UUID, MediaAsset>()

    override fun findById(id: UUID): MediaAsset? = assets[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<MediaAsset> =
        assets.values.filter { it.workspaceId == workspaceId }
    override fun findByFolderId(folderId: UUID?): List<MediaAsset> =
        assets.values.filter { it.folderId == folderId }
    override fun findStarred(workspaceId: UUID): List<MediaAsset> =
        assets.values.filter { it.workspaceId == workspaceId && it.isStarred }
    override fun findByMediaType(workspaceId: UUID, mediaType: MediaType): List<MediaAsset> =
        assets.values.filter { it.workspaceId == workspaceId && it.mediaType == mediaType }
    override fun search(workspaceId: UUID, query: String): List<MediaAsset> =
        assets.values.filter { it.workspaceId == workspaceId && it.filename.contains(query, ignoreCase = true) }
    override fun save(asset: MediaAsset): MediaAsset { assets[asset.id] = asset; return asset }
    override fun update(asset: MediaAsset): MediaAsset { assets[asset.id] = asset; return asset }
    override fun delete(id: UUID) { assets.remove(id) }
}

class MediaFolderInMemoryRepository : MediaFolderRepository {
    private val folders = mutableMapOf<UUID, MediaFolder>()

    override fun findById(id: UUID): MediaFolder? = folders[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<MediaFolder> =
        folders.values.filter { it.workspaceId == workspaceId }
    override fun findByParentFolderId(parentFolderId: UUID?): List<MediaFolder> =
        folders.values.filter { it.parentFolderId == parentFolderId }
    override fun save(folder: MediaFolder): MediaFolder { folders[folder.id] = folder; return folder }
    override fun update(folder: MediaFolder): MediaFolder { folders[folder.id] = folder; return folder }
    override fun delete(id: UUID) { folders.remove(id) }
}

class MediaAssetVersionInMemoryRepository : MediaAssetVersionRepository {
    private val versions = mutableMapOf<UUID, MediaAssetVersion>()

    override fun findByMediaAssetId(mediaAssetId: UUID): List<MediaAssetVersion> =
        versions.values.filter { it.mediaAssetId == mediaAssetId }.sortedByDescending { it.versionNumber }
    override fun findLatestByMediaAssetId(mediaAssetId: UUID): MediaAssetVersion? =
        versions.values.filter { it.mediaAssetId == mediaAssetId }.maxByOrNull { it.versionNumber }
    override fun save(version: MediaAssetVersion): MediaAssetVersion { versions[version.id] = version; return version }
}
