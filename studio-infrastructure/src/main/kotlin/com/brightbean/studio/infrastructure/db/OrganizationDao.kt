package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.config.RegisterBeanMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterBeanMapper(OrganizationDto::class)
interface OrganizationDao {
    @SqlQuery("SELECT * FROM organization WHERE id = :id")
    fun findById(id: UUID): OrganizationDto?

    @SqlQuery("SELECT * FROM organization WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<OrganizationDto>

    @SqlUpdate("INSERT INTO organization (id, workspace_id, name, logo_url, website, created_at) VALUES (:dto.id, :dto.workspaceId, :dto.name, :dto.logoUrl, :dto.website, :dto.createdAt)")
    fun insert(dto: OrganizationDto)

    @SqlUpdate("DELETE FROM organization WHERE id = :id")
    fun delete(id: UUID)
}

data class OrganizationDto(
    val id: UUID,
    val workspaceId: UUID,
    val name: String,
    val logoUrl: String?,
    val website: String?,
    val createdAt: java.time.Instant,
)
