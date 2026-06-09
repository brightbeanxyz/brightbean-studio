package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.WorkspaceSetting
import java.util.UUID

interface WorkspaceSettingRepository {
    fun findByWorkspaceId(workspaceId: UUID): List<WorkspaceSetting>
    fun findByKey(workspaceId: UUID, key: String): WorkspaceSetting?
    fun save(setting: WorkspaceSetting): WorkspaceSetting
    fun update(setting: WorkspaceSetting): WorkspaceSetting
}
