package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.OrgSetting
import com.brightbean.studio.domain.model.WorkspaceSetting
import com.brightbean.studio.domain.repository.OrgSettingRepository
import com.brightbean.studio.domain.repository.WorkspaceSettingRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIOrgSettingRepository(jdbi: Jdbi) : OrgSettingRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: OrgSettingDao by lazy { jdbi.onDemand(OrgSettingDao::class.java) }

    override fun findByOrganizationId(organizationId: UUID): List<OrgSetting> = dao.findByOrganizationId(organizationId).map { it.toDomain() }
    override fun findByKey(organizationId: UUID, key: String): OrgSetting? = dao.findByKey(organizationId, key)?.toDomain()
    override fun save(setting: OrgSetting): OrgSetting { dao.insert(setting.toDto()); return setting }
    override fun update(setting: OrgSetting): OrgSetting { dao.update(setting.toDto()); return setting }

    private fun OrgSetting.toDto() = OrgSettingDto(id, organizationId, key, value, updatedAt)
    private fun OrgSettingDto.toDomain() = OrgSetting(id, organizationId, key, value, updatedAt)
}

class JDBIWorkspaceSettingRepository(jdbi: Jdbi) : WorkspaceSettingRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: WorkspaceSettingDao by lazy { jdbi.onDemand(WorkspaceSettingDao::class.java) }

    override fun findByWorkspaceId(workspaceId: UUID): List<WorkspaceSetting> = dao.findByWorkspaceId(workspaceId).map { it.toDomain() }
    override fun findByKey(workspaceId: UUID, key: String): WorkspaceSetting? = dao.findByKey(workspaceId, key)?.toDomain()
    override fun save(setting: WorkspaceSetting): WorkspaceSetting { dao.insert(setting.toDto()); return setting }
    override fun update(setting: WorkspaceSetting): WorkspaceSetting { dao.update(setting.toDto()); return setting }

    private fun WorkspaceSetting.toDto() = WorkspaceSettingDto(id, workspaceId, key, value, updatedAt)
    private fun WorkspaceSettingDto.toDomain() = WorkspaceSetting(id, workspaceId, key, value, updatedAt)
}
