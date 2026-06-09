package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.OrgSetting
import java.util.UUID

interface OrgSettingRepository {
    fun findByOrganizationId(organizationId: UUID): List<OrgSetting>
    fun findByKey(organizationId: UUID, key: String): OrgSetting?
    fun save(setting: OrgSetting): OrgSetting
    fun update(setting: OrgSetting): OrgSetting
}
