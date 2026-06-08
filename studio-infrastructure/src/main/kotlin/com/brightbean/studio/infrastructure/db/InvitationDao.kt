package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(InvitationDto::class)
interface InvitationDao {
    @SqlQuery("SELECT * FROM invitation WHERE id = :id")
    fun findById(id: UUID): InvitationDto?

    @SqlQuery("SELECT * FROM invitation WHERE token = :token")
    fun findByToken(token: String): InvitationDto?

    @SqlQuery("SELECT * FROM invitation WHERE organization_id = :organizationId")
    fun findByOrganizationId(organizationId: UUID): List<InvitationDto>

    @SqlUpdate("""
        INSERT INTO invitation (id, organization_id, email, org_role, workspace_assignments, invited_by, token, expires_at, accepted_at, status, created_at)
        VALUES (:dto.id, :dto.organizationId, :dto.email, :dto.orgRole, :dto.workspaceAssignments, :dto.invitedBy, :dto.token, :dto.expiresAt, :dto.acceptedAt, :dto.status, :dto.createdAt)
    """)
    fun insert(dto: InvitationDto)

    @SqlUpdate("""
        UPDATE invitation SET
            email = :dto.email,
            org_role = :dto.orgRole,
            workspace_assignments = :dto.workspaceAssignments,
            invited_by = :dto.invitedBy,
            expires_at = :dto.expiresAt,
            accepted_at = :dto.acceptedAt,
            status = :dto.status
        WHERE id = :dto.id
    """)
    fun update(dto: InvitationDto)

    @SqlUpdate("DELETE FROM invitation WHERE id = :id")
    fun delete(id: UUID)
}

data class InvitationDto(
    val id: UUID,
    val organizationId: UUID,
    val email: String,
    val orgRole: String,
    val workspaceAssignments: String,
    val invitedBy: UUID?,
    val token: String,
    val expiresAt: java.time.Instant,
    val acceptedAt: java.time.Instant?,
    val status: String,
    val createdAt: java.time.Instant,
)
