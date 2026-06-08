package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Organization
import java.util.UUID

interface OrganizationRepository {
    fun findById(id: UUID): Organization?
    fun save(organization: Organization): Organization
    fun update(organization: Organization): Organization
    fun delete(id: UUID)
}
