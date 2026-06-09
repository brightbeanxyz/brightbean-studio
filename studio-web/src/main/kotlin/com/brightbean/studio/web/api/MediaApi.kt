package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.MediaLibraryUseCases
import com.brightbean.studio.domain.model.MediaType
import com.brightbean.studio.web.api.dto.ErrorResponse
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import java.io.InputStreamReader
import java.time.Instant
import java.util.UUID

class MediaApi(
    private val mediaLibraryUseCases: MediaLibraryUseCases,
) : HttpHandler {

    private val gson: Gson = GsonBuilder()
        .registerTypeAdapter(Instant::class.java, InstantAdapter())
        .create()

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        val method = exchange.requestMethod

        when {
            path.matches(Regex("^/api/workspaces/[^/]+/media/folders$")) && method == "GET" -> listFolders(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/folders$")) && method == "POST" -> createFolder(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/folders/[^/]+$")) && method == "PUT" -> renameFolder(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/folders/[^/]+$")) && method == "DELETE" -> deleteFolder(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/[^/]+/versions$")) && method == "GET" -> listVersions(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/[^/]+/star$")) && method == "POST" -> starAsset(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/[^/]+/move$")) && method == "POST" -> moveAsset(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/[^/]+$")) && method == "PUT" -> updateAsset(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media/[^/]+$")) && method == "DELETE" -> deleteAsset(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media$")) && method == "GET" -> listAssets(exchange)
            path.matches(Regex("^/api/workspaces/[^/]+/media$")) && method == "POST" -> uploadAsset(exchange)
            else -> sendError(exchange, 404, "Not Found")
        }
    }

    private fun listAssets(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])
            val params = parseQueryParams(exchange.requestURI.query ?: "")

            val folderId = params["folder"]?.let { UUID.fromString(it) }
            val mediaType = params["type"]?.let { MediaType.valueOf(it.uppercase()) }
            val starredOnly = params["starred"]?.toBooleanStrictOrNull() == true
            val query = params["q"]

            val assets = mediaLibraryUseCases.listAssets(workspaceId, folderId, mediaType, starredOnly, query)
            sendJson(exchange, 200, assets)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun uploadAsset(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UploadAssetRequest::class.java)

            val asset = mediaLibraryUseCases.uploadAsset(
                workspaceId = workspaceId,
                filename = request.filename,
                mediaType = MediaType.valueOf(request.mediaType.uppercase()),
                mimeType = request.mimeType,
                fileSize = request.fileSize,
                filePath = request.filePath,
                uploadedBy = request.uploadedBy,
                folderId = request.folderId,
                width = request.width ?: 0,
                height = request.height ?: 0,
                thumbnailPath = request.thumbnailPath ?: "",
                altText = request.altText ?: "",
                title = request.title ?: "",
                tags = request.tags ?: emptyList(),
            )
            sendJson(exchange, 201, asset)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to upload asset")
        }
    }

    private fun updateAsset(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val assetId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, UpdateAssetRequest::class.java)

            val asset = mediaLibraryUseCases.updateAsset(assetId, request.altText, request.title, request.tags)
            sendJson(exchange, 200, asset)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to update asset")
        }
    }

    private fun deleteAsset(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val assetId = UUID.fromString(pathParts[5])

            mediaLibraryUseCases.deleteAsset(assetId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete asset")
        }
    }

    private fun starAsset(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val assetId = UUID.fromString(pathParts[5])

            val asset = mediaLibraryUseCases.starAsset(assetId)
            sendJson(exchange, 200, asset)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to star asset")
        }
    }

    private fun moveAsset(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val assetId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, MoveAssetRequest::class.java)

            val asset = mediaLibraryUseCases.moveAsset(assetId, request.folderId)
            sendJson(exchange, 200, asset)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to move asset")
        }
    }

    private fun listFolders(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val folders = mediaLibraryUseCases.listFolders(workspaceId)
            sendJson(exchange, 200, folders)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun createFolder(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val workspaceId = UUID.fromString(pathParts[3])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, CreateFolderRequest::class.java)

            val folder = mediaLibraryUseCases.createFolder(workspaceId, request.name, request.parentFolderId)
            sendJson(exchange, 201, folder)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to create folder")
        }
    }

    private fun renameFolder(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val folderId = UUID.fromString(pathParts[5])

            val body = InputStreamReader(exchange.requestBody).readText()
            val request = gson.fromJson(body, RenameFolderRequest::class.java)

            val folder = mediaLibraryUseCases.renameFolder(folderId, request.name)
            sendJson(exchange, 200, folder)
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to rename folder")
        }
    }

    private fun deleteFolder(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val folderId = UUID.fromString(pathParts[5])

            mediaLibraryUseCases.deleteFolder(folderId)
            sendJson(exchange, 200, mapOf("deleted" to true))
        } catch (e: Exception) {
            sendError(exchange, 400, e.message ?: "Failed to delete folder")
        }
    }

    private fun listVersions(exchange: HttpExchange) {
        try {
            val pathParts = exchange.requestURI.path.split("/")
            val assetId = UUID.fromString(pathParts[5])

            val versions = mediaLibraryUseCases.listVersions(assetId)
            sendJson(exchange, 200, versions)
        } catch (e: Exception) {
            sendError(exchange, 500, e.message ?: "Internal server error")
        }
    }

    private fun sendJson(exchange: HttpExchange, statusCode: Int, data: Any) {
        val json = gson.toJson(data)
        exchange.responseHeaders.set("Content-Type", "application/json")
        exchange.sendResponseHeaders(statusCode, json.toByteArray().size.toLong())
        exchange.responseBody.use { it.write(json.toByteArray()) }
    }

    private fun sendError(exchange: HttpExchange, statusCode: Int, message: String) {
        val error = ErrorResponse(
            error = when (statusCode) {
                400 -> "Bad Request"
                403 -> "Forbidden"
                404 -> "Not Found"
                500 -> "Internal Server Error"
                else -> "Error"
            },
            message = message,
            statusCode = statusCode,
        )
        sendJson(exchange, statusCode, error)
    }

    private fun parseQueryParams(query: String): Map<String, String> {
        if (query.isBlank()) return emptyMap()
        return query.split("&")
            .mapNotNull { param ->
                val parts = param.split("=")
                if (parts.size == 2) parts[0] to parts[1] else null
            }
            .toMap()
    }

    private data class UploadAssetRequest(
        val filename: String,
        val mediaType: String,
        val mimeType: String,
        val fileSize: Long,
        val filePath: String,
        val uploadedBy: UUID?,
        val folderId: UUID? = null,
        val width: Int? = null,
        val height: Int? = null,
        val thumbnailPath: String? = null,
        val altText: String? = null,
        val title: String? = null,
        val tags: List<String>? = null,
    )

    private data class UpdateAssetRequest(
        val altText: String? = null,
        val title: String? = null,
        val tags: List<String>? = null,
    )

    private data class MoveAssetRequest(val folderId: UUID?)
    private data class CreateFolderRequest(val name: String, val parentFolderId: UUID? = null)
    private data class RenameFolderRequest(val name: String)
}
