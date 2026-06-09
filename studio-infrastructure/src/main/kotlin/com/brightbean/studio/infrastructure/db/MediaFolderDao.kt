package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(MediaFolderDto::class)
interface MediaFolderDao {
    @SqlQuery("SELECT * FROM media_library_folder WHERE id = :id")
    fun findById(id: UUID): MediaFolderDto?

    @SqlQuery("SELECT * FROM media_library_folder WHERE workspace_id = :workspaceId ORDER BY name")
    fun findByWorkspaceId(workspaceId: UUID): List<MediaFolderDto>

    @SqlQuery("SELECT * FROM media_library_folder WHERE parent_folder_id IS NOT DISTINCT FROM :parentFolderId ORDER BY name")
    fun findByParentFolderId(parentFolderId: UUID?): List<MediaFolderDto>

    @SqlUpdate("""
        INSERT INTO media_library_folder (id, organization_id, workspace_id, parent_folder_id, name, created_at, updated_at)
        VALUES (:dto.id, :dto.organizationId, :dto.workspaceId, :dto.parentFolderId, :dto.name, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: MediaFolderDto)

    @SqlUpdate("""
        UPDATE media_library_folder SET
            name = :dto.name,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: MediaFolderDto)

    @SqlUpdate("DELETE FROM media_library_folder WHERE id = :id")
    fun delete(id: UUID)
}

data class MediaFolderDto(
    val id: UUID,
    val organizationId: UUID,
    val workspaceId: UUID?,
    val parentFolderId: UUID?,
    val name: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
