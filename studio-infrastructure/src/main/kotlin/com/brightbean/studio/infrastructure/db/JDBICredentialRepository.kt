package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Credential
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.repository.CredentialRepository
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBICredentialRepository(jdbi: Jdbi) : CredentialRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: CredentialDao by lazy { jdbi.onDemand(CredentialDao::class.java) }

    override fun findById(id: UUID): Credential? =
        dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Credential> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): Credential? =
        dao.findByWorkspaceAndPlatform(workspaceId, platformType.name)?.toDomain()

    override fun save(credential: Credential): Credential {
        dao.insert(credential.toDto())
        return credential
    }

    override fun update(credential: Credential): Credential {
        dao.update(credential.toDto())
        return credential
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun Credential.toDto() = CredentialDto(
        id = id,
        workspaceId = workspaceId,
        platformType = platformType.name,
        encryptedAccessToken = encryptedAccessToken,
        encryptedRefreshToken = encryptedRefreshToken,
        tokenExpiresAt = tokenExpiresAt,
        metadata = objectMapper.writeValueAsString(metadata),
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun CredentialDto.toDomain(): Credential {
        val meta: Map<String, String> = try {
            objectMapper.readValue(metadata, objectMapper.typeFactory.constructMapType(Map::class.java, String::class.java, String::class.java))
        } catch (_: Exception) {
            emptyMap()
        }
        return Credential(
            id = id,
            workspaceId = workspaceId,
            platformType = PlatformType.valueOf(platformType),
            encryptedAccessToken = encryptedAccessToken,
            encryptedRefreshToken = encryptedRefreshToken,
            tokenExpiresAt = tokenExpiresAt,
            metadata = meta,
            createdAt = createdAt,
            updatedAt = updatedAt,
        )
    }
}
