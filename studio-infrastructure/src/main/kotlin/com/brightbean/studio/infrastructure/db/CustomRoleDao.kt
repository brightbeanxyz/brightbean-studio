package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(CustomRoleDto::class)
interface CustomRoleDao {
    @SqlQuery("SELECT * FROM custom_role WHERE id = :id")
    fun findById(id: UUID): CustomRoleDto?

    @SqlQuery("SELECT * FROM custom_role WHERE organization_id = :organizationId")
    fun findByOrganizationId(organizationId: UUID): List<CustomRoleDto>

    @SqlUpdate("""
        INSERT INTO custom_role (id, organization_id, name, permissions, created_at, updated_at)
        VALUES (:dto.id, :dto.organizationId, :dto.name, :dto.permissions, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: CustomRoleDto)

    @SqlUpdate("""
        UPDATE custom_role SET
            name = :dto.name,
            permissions = :dto.permissions,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: CustomRoleDto)

    @SqlUpdate("DELETE FROM custom_role WHERE id = :id")
    fun delete(id: UUID)
}

data class CustomRoleDto(
    val id: UUID,
    val organizationId: UUID,
    val name: String,
    val permissions: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
