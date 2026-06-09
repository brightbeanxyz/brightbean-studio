package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.OrgSetting
import com.brightbean.studio.domain.model.WorkspaceSetting
import com.brightbean.studio.domain.repository.OrgSettingRepository
import com.brightbean.studio.domain.repository.WorkspaceSettingRepository
import java.time.Instant
import java.util.UUID

class SettingsUseCases(
    private val orgSettingRepository: OrgSettingRepository,
    private val workspaceSettingRepository: WorkspaceSettingRepository,
) {
    fun getOrgSettings(organizationId: UUID): List<OrgSetting> = orgSettingRepository.findByOrganizationId(organizationId)
    fun getOrgSetting(organizationId: UUID, key: String): OrgSetting? = orgSettingRepository.findByKey(organizationId, key)

    fun setOrgSetting(organizationId: UUID, key: String, value: String): OrgSetting {
        val existing = orgSettingRepository.findByKey(organizationId, key)
        return if (existing != null) {
            orgSettingRepository.update(existing.copy(value = value, updatedAt = Instant.now()))
        } else {
            orgSettingRepository.save(OrgSetting(id = UUID.randomUUID(), organizationId = organizationId, key = key, value = value, updatedAt = Instant.now()))
        }
    }

    fun getWorkspaceSettings(workspaceId: UUID): List<WorkspaceSetting> = workspaceSettingRepository.findByWorkspaceId(workspaceId)
    fun getWorkspaceSetting(workspaceId: UUID, key: String): WorkspaceSetting? = workspaceSettingRepository.findByKey(workspaceId, key)

    fun setWorkspaceSetting(workspaceId: UUID, key: String, value: String?): WorkspaceSetting {
        val existing = workspaceSettingRepository.findByKey(workspaceId, key)
        return if (existing != null) {
            workspaceSettingRepository.update(existing.copy(value = value, updatedAt = Instant.now()))
        } else {
            workspaceSettingRepository.save(WorkspaceSetting(id = UUID.randomUUID(), workspaceId = workspaceId, key = key, value = value, updatedAt = Instant.now()))
        }
    }
}
