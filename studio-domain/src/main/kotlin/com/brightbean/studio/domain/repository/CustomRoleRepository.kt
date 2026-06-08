package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.CustomRole
import java.util.UUID

interface CustomRoleRepository {
    fun findById(id: UUID): CustomRole?
    fun findByOrganizationId(organizationId: UUID): List<CustomRole>
    fun save(customRole: CustomRole): CustomRole
    fun update(customRole: CustomRole): CustomRole
    fun delete(id: UUID)
}
