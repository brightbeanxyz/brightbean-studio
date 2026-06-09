package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.MediaAsset
import com.brightbean.studio.domain.model.MediaType
import java.util.UUID

interface MediaAssetRepository {
    fun findById(id: UUID): MediaAsset?
    fun findByWorkspaceId(workspaceId: UUID): List<MediaAsset>
    fun findByFolderId(folderId: UUID?): List<MediaAsset>
    fun findStarred(workspaceId: UUID): List<MediaAsset>
    fun findByMediaType(workspaceId: UUID, mediaType: MediaType): List<MediaAsset>
    fun search(workspaceId: UUID, query: String): List<MediaAsset>
    fun save(asset: MediaAsset): MediaAsset
    fun update(asset: MediaAsset): MediaAsset
    fun delete(id: UUID)
}
