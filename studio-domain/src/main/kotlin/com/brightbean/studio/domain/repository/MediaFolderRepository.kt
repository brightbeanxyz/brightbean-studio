package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.MediaFolder
import java.util.UUID

interface MediaFolderRepository {
    fun findById(id: UUID): MediaFolder?
    fun findByWorkspaceId(workspaceId: UUID): List<MediaFolder>
    fun findByParentFolderId(parentFolderId: UUID?): List<MediaFolder>
    fun save(folder: MediaFolder): MediaFolder
    fun update(folder: MediaFolder): MediaFolder
    fun delete(id: UUID)
}
