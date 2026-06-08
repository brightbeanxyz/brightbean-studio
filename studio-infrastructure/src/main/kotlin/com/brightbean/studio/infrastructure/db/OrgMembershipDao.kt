package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(OrgMembershipDto::class)
interface OrgMembershipDao {
    @SqlQuery("SELECT * FROM org_membership WHERE id = :id")
    fun findById(id: UUID): OrgMembershipDto?

    @SqlQuery("SELECT * FROM org_membership WHERE user_id = :userId")
    fun findByUserId(userId: UUID): List<OrgMembershipDto>

    @SqlQuery("SELECT * FROM org_membership WHERE organization_id = :organizationId")
    fun findByOrganizationId(organizationId: UUID): List<OrgMembershipDto>

    @SqlQuery("SELECT * FROM org_membership WHERE user_id = :userId AND organization_id = :organizationId")
    fun findByUserAndOrganization(userId: UUID, organizationId: UUID): OrgMembershipDto?

    @SqlUpdate("""
        INSERT INTO org_membership (id, user_id, organization_id, org_role, invited_at, accepted_at)
        VALUES (:dto.id, :dto.userId, :dto.organizationId, :dto.orgRole, :dto.invitedAt, :dto.acceptedAt)
    """)
    fun insert(dto: OrgMembershipDto)

    @SqlUpdate("""
        UPDATE org_membership SET
            org_role = :dto.orgRole,
            accepted_at = :dto.acceptedAt
        WHERE id = :dto.id
    """)
    fun update(dto: OrgMembershipDto)

    @SqlUpdate("DELETE FROM org_membership WHERE id = :id")
    fun delete(id: UUID)
}

data class OrgMembershipDto(
    val id: UUID,
    val userId: UUID,
    val organizationId: UUID,
    val orgRole: String,
    val invitedAt: java.time.Instant,
    val acceptedAt: java.time.Instant?,
)
