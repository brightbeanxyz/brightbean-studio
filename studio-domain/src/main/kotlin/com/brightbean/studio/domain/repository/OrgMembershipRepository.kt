package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.OrgMembership
import java.util.UUID

interface OrgMembershipRepository {
    fun findById(id: UUID): OrgMembership?
    fun findByUserId(userId: UUID): List<OrgMembership>
    fun findByOrganizationId(organizationId: UUID): List<OrgMembership>
    fun findByUserAndOrganization(userId: UUID, organizationId: UUID): OrgMembership?
    fun save(membership: OrgMembership): OrgMembership
    fun update(membership: OrgMembership): OrgMembership
    fun delete(id: UUID)
}
