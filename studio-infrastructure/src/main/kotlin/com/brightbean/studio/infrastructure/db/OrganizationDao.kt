package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(OrganizationDto::class)
interface OrganizationDao {
    @SqlQuery("SELECT * FROM organization WHERE id = :id")
    fun findById(id: UUID): OrganizationDto?

    @SqlUpdate("""
        INSERT INTO organization (id, name, logo_url, default_timezone, billing_email, created_at, updated_at)
        VALUES (:dto.id, :dto.name, :dto.logoUrl, :dto.defaultTimezone, :dto.billingEmail, :dto.createdAt, :dto.updatedAt)
    """)
    fun insert(dto: OrganizationDto)

    @SqlUpdate("""
        UPDATE organization SET
            name = :dto.name,
            logo_url = :dto.logoUrl,
            default_timezone = :dto.defaultTimezone,
            billing_email = :dto.billingEmail,
            updated_at = :dto.updatedAt
        WHERE id = :dto.id
    """)
    fun update(dto: OrganizationDto)

    @SqlUpdate("DELETE FROM organization WHERE id = :id")
    fun delete(id: UUID)
}

data class OrganizationDto(
    val id: UUID,
    val name: String,
    val logoUrl: String?,
    val defaultTimezone: String,
    val billingEmail: String,
    val createdAt: java.time.Instant,
    val updatedAt: java.time.Instant,
)
