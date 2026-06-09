package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.repository.UserRepository
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIUserRepository(jdbi: Jdbi) : UserRepository {

    private val objectMapper = jacksonObjectMapper()

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val userDao: UserDao by lazy { jdbi.onDemand(UserDao::class.java) }

    override fun findById(id: UUID): User? =
        userDao.findById(id)?.toDomain()

    override fun findByEmail(email: String): User? =
        userDao.findByEmail(email)?.toDomain()

    override fun save(user: User): User {
        userDao.insert(user.toDto())
        return user
    }

    override fun update(user: User): User {
        userDao.update(user.toDto())
        return user
    }

    override fun delete(id: UUID) {
        userDao.delete(id)
    }

    private fun User.toDto() = UserDto(
        id = id,
        email = email,
        name = name,
        passwordHash = passwordHash,
        avatar = avatar,
        totpSecret = totpSecret,
        totpRecoveryCodes = totpRecoveryCodes?.let { objectMapper.writeValueAsString(it) },
        totpEnabled = totpEnabled,
        lastWorkspaceId = lastWorkspaceId,
        tosAcceptedAt = tosAcceptedAt,
        isActive = isActive,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )

    private fun UserDto.toDomain() = User(
        id = id,
        email = email,
        name = name,
        passwordHash = passwordHash,
        avatar = avatar,
        totpSecret = totpSecret,
        totpRecoveryCodes = totpRecoveryCodes?.let {
            objectMapper.readValue(it, objectMapper.typeFactory.constructCollectionType(List::class.java, String::class.java))
        },
        totpEnabled = totpEnabled,
        lastWorkspaceId = lastWorkspaceId,
        tosAcceptedAt = tosAcceptedAt,
        isActive = isActive,
        createdAt = createdAt,
        updatedAt = updatedAt,
    )
}
