package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.time.Instant
import java.util.UUID

@RegisterKotlinMapper(OrgSettingDto::class)
interface OrgSettingDao {
    @SqlQuery("SELECT * FROM settings_org_setting WHERE organization_id = :organizationId ORDER BY key")
    fun findByOrganizationId(organizationId: UUID): List<OrgSettingDto>

    @SqlQuery("SELECT * FROM settings_org_setting WHERE organization_id = :organizationId AND key = :key")
    fun findByKey(organizationId: UUID, key: String): OrgSettingDto?

    @SqlUpdate("""
        INSERT INTO settings_org_setting (id, organization_id, key, value, updated_at)
        VALUES (:dto.id, :dto.organizationId, :dto.key, :dto.value, :dto.updatedAt)
    """)
    fun insert(dto: OrgSettingDto)

    @SqlUpdate("""
        UPDATE settings_org_setting SET value = :dto.value, updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: OrgSettingDto)
}

data class OrgSettingDto(
    val id: UUID,
    val organizationId: UUID,
    val key: String,
    val value: String,
    val updatedAt: Instant,
)

@RegisterKotlinMapper(WorkspaceSettingDto::class)
interface WorkspaceSettingDao {
    @SqlQuery("SELECT * FROM settings_workspace_setting WHERE workspace_id = :workspaceId ORDER BY key")
    fun findByWorkspaceId(workspaceId: UUID): List<WorkspaceSettingDto>

    @SqlQuery("SELECT * FROM settings_workspace_setting WHERE workspace_id = :workspaceId AND key = :key")
    fun findByKey(workspaceId: UUID, key: String): WorkspaceSettingDto?

    @SqlUpdate("""
        INSERT INTO settings_workspace_setting (id, workspace_id, key, value, updated_at)
        VALUES (:dto.id, :dto.workspaceId, :dto.key, :dto.value, :dto.updatedAt)
    """)
    fun insert(dto: WorkspaceSettingDto)

    @SqlUpdate("""
        UPDATE settings_workspace_setting SET value = :dto.value, updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: WorkspaceSettingDto)
}

data class WorkspaceSettingDto(
    val id: UUID,
    val workspaceId: UUID,
    val key: String,
    val value: String?,
    val updatedAt: Instant,
)
