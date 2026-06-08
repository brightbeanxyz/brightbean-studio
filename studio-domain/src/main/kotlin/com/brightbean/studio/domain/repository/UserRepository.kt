package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.User
import java.util.UUID

interface UserRepository {
    fun findById(id: UUID): User?
    fun findByEmail(email: String): User?
    fun save(user: User): User
    fun update(user: User): User
    fun delete(id: UUID)
}
