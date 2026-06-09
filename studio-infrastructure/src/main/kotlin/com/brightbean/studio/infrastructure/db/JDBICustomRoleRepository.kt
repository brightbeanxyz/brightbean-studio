package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.CustomRole
import com.brightbean.studio.domain.repository.CustomRoleRepository
import com.fasterxml.jackson.core.type.TypeReference
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBICustomRoleRepository(jdbi: Jdbi) : CustomRoleRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: CustomRoleDao by lazy { jdbi.onDemand(CustomRoleDao::class.java) }

    override fun findById(id: UUID): CustomRole? =
        dao.findById(id)?.toDomain()

    override fun findByOrganizationId(organizationId: UUID): List<CustomRole> =
        dao.findByOrganizationId(organizationId).map { it.toDomain() }

    override fun save(role: CustomRole): CustomRole {
        dao.insert(role.toDto())
        return role
    }

    override fun update(role: CustomRole): CustomRole {
        dao.update(role.toDto())
        return role
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun CustomRole.toDto() = CustomRoleDto(
        id = id,
        organizationId = organizationId,
        name = name,
        permissions = objectMapper.writeValueAsString(permissions),
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun CustomRoleDto.toDomain(): CustomRole {
        val perms: Map<String, Boolean> = objectMapper.readValue(
            permissions,
            object : TypeReference<Map<String, Boolean>>() {}
        )
        return CustomRole(
            id = id,
            organizationId = organizationId,
            name = name,
            permissions = perms,
            createdAt = createdAt,
            updatedAt = updatedAt,
        )
    }
}
