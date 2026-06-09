package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.MediaFolder
import com.brightbean.studio.domain.repository.MediaFolderRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIMediaFolderRepository(jdbi: Jdbi) : MediaFolderRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: MediaFolderDao by lazy { jdbi.onDemand(MediaFolderDao::class.java) }

    override fun findById(id: UUID): MediaFolder? = dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<MediaFolder> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByParentFolderId(parentFolderId: UUID?): List<MediaFolder> =
        dao.findByParentFolderId(parentFolderId).map { it.toDomain() }

    override fun save(folder: MediaFolder): MediaFolder {
        dao.insert(folder.toDto())
        return folder
    }

    override fun update(folder: MediaFolder): MediaFolder {
        dao.update(folder.toDto())
        return folder
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun MediaFolder.toDto() = MediaFolderDto(
        id = id, organizationId = organizationId, workspaceId = workspaceId,
        parentFolderId = parentFolderId, name = name,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun MediaFolderDto.toDomain() = MediaFolder(
        id = id, organizationId = organizationId, workspaceId = workspaceId,
        parentFolderId = parentFolderId, name = name,
        createdAt = createdAt, updatedAt = updatedAt,
    )
}
