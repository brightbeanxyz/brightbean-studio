package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.MediaLibraryUseCases
import com.brightbean.studio.domain.model.MediaAsset
import com.brightbean.studio.domain.model.MediaFolder
import com.brightbean.studio.domain.model.MediaType
import com.brightbean.studio.domain.model.ProcessingStatus
import com.brightbean.studio.domain.repository.MediaAssetRepository
import com.brightbean.studio.domain.repository.MediaAssetVersionRepository
import com.brightbean.studio.domain.repository.MediaFolderRepository
import com.brightbean.studio.web.server.Middleware
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Instant
import java.util.UUID

class MediaApiTest {

    @Test
    fun `list assets returns 200 with empty list`() {
        val workspaceId = UUID.randomUUID()
        val assetRepo = MediaAssetApiInMemoryRepository()
        val folderRepo = MediaFolderApiInMemoryRepository()
        val versionRepo = MediaAssetVersionApiInMemoryRepository()
        val useCases = MediaLibraryUseCases(assetRepo, folderRepo, versionRepo)
        val api = MediaApi(useCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8089/api/workspaces/${workspaceId}/media"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertEquals("[]", response.body())
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `upload asset returns 201`() {
        val workspaceId = UUID.randomUUID()
        val assetRepo = MediaAssetApiInMemoryRepository()
        val folderRepo = MediaFolderApiInMemoryRepository()
        val versionRepo = MediaAssetVersionApiInMemoryRepository()
        val useCases = MediaLibraryUseCases(assetRepo, folderRepo, versionRepo)
        val api = MediaApi(useCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val body = """{"filename":"photo.jpg","mediaType":"IMAGE","mimeType":"image/jpeg","fileSize":1024,"filePath":"/uploads/photo.jpg"}"""
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8089/api/workspaces/${workspaceId}/media"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(201, response.statusCode())
            assertTrue(response.body().contains("photo.jpg"))
        } finally {
            server.stop(0)
        }
    }

    @Test
    fun `list folders returns 200 with items`() {
        val workspaceId = UUID.randomUUID()
        val assetRepo = MediaAssetApiInMemoryRepository()
        val folderRepo = MediaFolderApiInMemoryRepository()
        val versionRepo = MediaAssetVersionApiInMemoryRepository()
        val now = Instant.now()
        folderRepo.save(MediaFolder(
            id = UUID.randomUUID(),
            organizationId = UUID.randomUUID(),
            workspaceId = workspaceId,
            parentFolderId = null,
            name = "Images",
            createdAt = now,
            updatedAt = now,
        ))
        val useCases = MediaLibraryUseCases(assetRepo, folderRepo, versionRepo)
        val api = MediaApi(useCases)
        val handler = Middleware.corsMiddleware(listOf("*"), api)
        val server = createTestServer(handler)
        server.start()
        try {
            val client = HttpClient.newHttpClient()
            val request = HttpRequest.newBuilder()
                .uri(URI("http://localhost:8089/api/workspaces/${workspaceId}/media/folders"))
                .GET()
                .build()
            val response = client.send(request, HttpResponse.BodyHandlers.ofString())

            assertEquals(200, response.statusCode())
            assertTrue(response.body().contains("Images"))
        } finally {
            server.stop(0)
        }
    }

    private fun createTestServer(handler: com.sun.net.httpserver.HttpHandler): com.sun.net.httpserver.HttpServer {
        return com.sun.net.httpserver.HttpServer.create(
            java.net.InetSocketAddress("localhost", 8089), 0
        ).apply {
            createContext("/", handler)
            executor = null
        }
    }
}

class MediaAssetApiInMemoryRepository : MediaAssetRepository {
    private val assets = mutableMapOf<UUID, MediaAsset>()
    override fun findById(id: UUID): MediaAsset? = assets[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<MediaAsset> = assets.values.filter { it.workspaceId == workspaceId }
    override fun findByFolderId(folderId: UUID?): List<MediaAsset> = assets.values.filter { it.folderId == folderId }
    override fun findStarred(workspaceId: UUID): List<MediaAsset> = assets.values.filter { it.workspaceId == workspaceId && it.isStarred }
    override fun findByMediaType(workspaceId: UUID, mediaType: MediaType): List<MediaAsset> = assets.values.filter { it.workspaceId == workspaceId && it.mediaType == mediaType }
    override fun search(workspaceId: UUID, query: String): List<MediaAsset> = assets.values.filter { it.workspaceId == workspaceId && it.filename.contains(query, ignoreCase = true) }
    override fun save(asset: MediaAsset): MediaAsset { assets[asset.id] = asset; return asset }
    override fun update(asset: MediaAsset): MediaAsset { assets[asset.id] = asset; return asset }
    override fun delete(id: UUID) { assets.remove(id) }
}

class MediaFolderApiInMemoryRepository : MediaFolderRepository {
    private val folders = mutableMapOf<UUID, MediaFolder>()
    override fun findById(id: UUID): MediaFolder? = folders[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<MediaFolder> = folders.values.filter { it.workspaceId == workspaceId }
    override fun findByParentFolderId(parentFolderId: UUID?): List<MediaFolder> = folders.values.filter { it.parentFolderId == parentFolderId }
    override fun save(folder: MediaFolder): MediaFolder { folders[folder.id] = folder; return folder }
    override fun update(folder: MediaFolder): MediaFolder { folders[folder.id] = folder; return folder }
    override fun delete(id: UUID) { folders.remove(id) }
}

class MediaAssetVersionApiInMemoryRepository : MediaAssetVersionRepository {
    private val versions = mutableMapOf<UUID, com.brightbean.studio.domain.model.MediaAssetVersion>()
    override fun findByMediaAssetId(mediaAssetId: UUID): List<com.brightbean.studio.domain.model.MediaAssetVersion> =
        versions.values.filter { it.mediaAssetId == mediaAssetId }.sortedByDescending { it.versionNumber }
    override fun findLatestByMediaAssetId(mediaAssetId: UUID): com.brightbean.studio.domain.model.MediaAssetVersion? =
        versions.values.filter { it.mediaAssetId == mediaAssetId }.maxByOrNull { it.versionNumber }
    override fun save(version: com.brightbean.studio.domain.model.MediaAssetVersion): com.brightbean.studio.domain.model.MediaAssetVersion { versions[version.id] = version; return version }
}
