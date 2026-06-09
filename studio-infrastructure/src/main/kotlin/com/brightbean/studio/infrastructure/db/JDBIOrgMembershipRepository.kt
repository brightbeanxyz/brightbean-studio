package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.OrgMembership
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.repository.OrgMembershipRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIOrgMembershipRepository(jdbi: Jdbi) : OrgMembershipRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: OrgMembershipDao by lazy { jdbi.onDemand(OrgMembershipDao::class.java) }

    override fun findById(id: UUID): OrgMembership? =
        dao.findById(id)?.toDomain()

    override fun findByUserId(userId: UUID): List<OrgMembership> =
        dao.findByUserId(userId).map { it.toDomain() }

    override fun findByOrganizationId(organizationId: UUID): List<OrgMembership> =
        dao.findByOrganizationId(organizationId).map { it.toDomain() }

    override fun findByUserAndOrganization(userId: UUID, organizationId: UUID): OrgMembership? =
        dao.findByUserAndOrganization(userId, organizationId)?.toDomain()

    override fun save(membership: OrgMembership): OrgMembership {
        dao.insert(membership.toDto())
        return membership
    }

    override fun update(membership: OrgMembership): OrgMembership {
        dao.update(membership.toDto())
        return membership
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun OrgMembership.toDto() = OrgMembershipDto(
        id = id,
        userId = userId,
        organizationId = organizationId,
        orgRole = orgRole.name,
        invitedAt = invitedAt,
        acceptedAt = acceptedAt,
    )

    private fun OrgMembershipDto.toDomain() = OrgMembership(
        id = id,
        userId = userId,
        organizationId = organizationId,
        orgRole = OrgRole.valueOf(orgRole),
        invitedAt = invitedAt,
        acceptedAt = acceptedAt,
    )
}
