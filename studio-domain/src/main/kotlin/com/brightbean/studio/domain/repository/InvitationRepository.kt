package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Invitation
import java.util.UUID

interface InvitationRepository {
    fun findById(id: UUID): Invitation?
    fun findByToken(token: String): Invitation?
    fun findByOrganizationId(organizationId: UUID): List<Invitation>
    fun save(invitation: Invitation): Invitation
    fun update(invitation: Invitation): Invitation
    fun delete(id: UUID)
}
