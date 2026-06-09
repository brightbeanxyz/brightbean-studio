package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Organization
import com.brightbean.studio.domain.repository.OrganizationRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIOrganizationRepository(jdbi: Jdbi) : OrganizationRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: OrganizationDao by lazy { jdbi.onDemand(OrganizationDao::class.java) }

    override fun findById(id: UUID): Organization? =
        dao.findById(id)?.toDomain()

    override fun save(organization: Organization): Organization {
        dao.insert(organization.toDto())
        return organization
    }

    override fun update(organization: Organization): Organization {
        dao.update(organization.toDto())
        return organization
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun Organization.toDto() = OrganizationDto(
        id = id,
        name = name,
        logoUrl = logoUrl,
        defaultTimezone = defaultTimezone,
        billingEmail = billingEmail,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun OrganizationDto.toDomain() = Organization(
        id = id,
        name = name,
        logoUrl = logoUrl,
        defaultTimezone = defaultTimezone,
        billingEmail = billingEmail,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )
}
