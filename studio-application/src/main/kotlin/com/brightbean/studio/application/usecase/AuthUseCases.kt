package com.brightbean.studio.application.usecase

import at.favre.lib.crypto.bcrypt.BCrypt
import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.UserRepository
import java.security.SecureRandom
import java.time.Instant
import java.util.Base64
import java.util.UUID

class AuthUseCases(
    private val userRepository: UserRepository,
    private val sessionRepository: SessionRepository,
) {
    private val secureRandom = SecureRandom()

    companion object {
        private const val SESSION_TOKEN_BYTES = 48
        private const val SESSION_DURATION_HOURS = 24L
    }

    fun register(email: String, name: String, password: String): Result<User> {
        if (userRepository.findByEmail(email) != null) {
            return Result.failure(IllegalArgumentException("Email already registered: $email"))
        }
        val now = Instant.now()
        val user = User(
            id = UUID.randomUUID(),
            email = email,
            name = name,
            passwordHash = hashPassword(password),
            isActive = true,
            createdAt = now,
            updatedAt = now,
        )
        userRepository.save(user)
        return Result.success(user)
    }

    fun login(email: String, password: String): Result<String> {
        val user = userRepository.findByEmail(email)
            ?: return Result.failure(IllegalArgumentException("Invalid credentials"))
        if (!verifyPassword(password, user.passwordHash)) {
            return Result.failure(IllegalArgumentException("Invalid credentials"))
        }
        val token = generateSessionToken()
        val tokenHash = hashToken(token)
        val session = Session(
            id = UUID.randomUUID(),
            userId = user.id,
            tokenHash = tokenHash,
            expiresAt = Instant.now().plusSeconds(SESSION_DURATION_HOURS * 3600),
        )
        sessionRepository.save(session)
        return Result.success(token)
    }

    fun verifySession(token: String): User? {
        val tokenHash = hashToken(token)
        val session = sessionRepository.findByTokenHash(tokenHash) ?: return null
        if (session.isExpired) return null
        return userRepository.findById(session.userId)
    }

    fun logout(token: String) {
        val tokenHash = hashToken(token)
        val session = sessionRepository.findByTokenHash(tokenHash) ?: return
        sessionRepository.delete(session.id)
    }

    private fun hashPassword(password: String): String =
        BCrypt.withDefaults().hashToString(12, password.toCharArray())

    private fun verifyPassword(password: String, hash: String): Boolean =
        BCrypt.verifyer().verify(password.toCharArray(), hash).verified

    private fun generateSessionToken(): String {
        val bytes = ByteArray(SESSION_TOKEN_BYTES)
        secureRandom.nextBytes(bytes)
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes)
    }

    private fun hashToken(token: String): String {
        val bytes = token.toByteArray(Charsets.UTF_8)
        val digest = java.security.MessageDigest.getInstance("SHA-256").digest(bytes)
        return Base64.getEncoder().encodeToString(digest)
    }
}
