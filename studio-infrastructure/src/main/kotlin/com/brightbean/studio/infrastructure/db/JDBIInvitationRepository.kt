package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Invitation
import com.brightbean.studio.domain.model.InvitationStatus
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.repository.InvitationRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIInvitationRepository(jdbi: Jdbi) : InvitationRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: InvitationDao by lazy { jdbi.onDemand(InvitationDao::class.java) }

    override fun findById(id: UUID): Invitation? =
        dao.findById(id)?.toDomain()

    override fun findByToken(token: String): Invitation? =
        dao.findByToken(token)?.toDomain()

    override fun findByOrganizationId(organizationId: UUID): List<Invitation> =
        dao.findByOrganizationId(organizationId).map { it.toDomain() }

    override fun save(invitation: Invitation): Invitation {
        dao.insert(invitation.toDto())
        return invitation
    }

    override fun update(invitation: Invitation): Invitation {
        dao.update(invitation.toDto())
        return invitation
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun Invitation.toDto() = InvitationDto(
        id = id,
        organizationId = organizationId,
        email = email,
        orgRole = orgRole.name,
        workspaceAssignments = workspaceAssignments,
        invitedBy = invitedBy,
        token = token,
        expiresAt = expiresAt,
        acceptedAt = acceptedAt,
        status = status.name,
        createdAt = createdAt,
    )

    private fun InvitationDto.toDomain() = Invitation(
        id = id,
        organizationId = organizationId,
        email = email,
        orgRole = OrgRole.valueOf(orgRole),
        workspaceAssignments = workspaceAssignments,
        invitedBy = invitedBy,
        token = token,
        expiresAt = expiresAt,
        acceptedAt = acceptedAt,
        status = InvitationStatus.valueOf(status),
        createdAt = createdAt,
    )
}
