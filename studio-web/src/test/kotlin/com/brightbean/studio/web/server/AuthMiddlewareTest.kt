package com.brightbean.studio.web.server

import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.UserRepository
import com.sun.net.httpserver.HttpHandler
import com.sun.net.httpserver.HttpServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.net.InetSocketAddress
import java.net.URI
import java.net.http.HttpClient
import java.net.http.HttpRequest
import java.net.http.HttpResponse
import java.time.Instant
import java.util.UUID

class AuthMiddlewareTest {
    private lateinit var server: HttpServer
    private lateinit var userRepository: InMemoryUserRepository
    private lateinit var sessionRepository: InMemorySessionRepository
    private lateinit var authUseCases: AuthUseCases
    private var port: Int = 0
    private val client = HttpClient.newHttpClient()

    @BeforeEach
    fun setUp() {
        userRepository = InMemoryUserRepository()
        sessionRepository = InMemorySessionRepository()
        authUseCases = AuthUseCases(userRepository, sessionRepository)

        val okHandler = HttpHandler { exchange ->
            val response = """{"ok":true}"""
            exchange.responseHeaders.set("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, response.toByteArray().size.toLong())
            exchange.responseBody.use { it.write(response.toByteArray()) }
        }

        val publicPaths = setOf("/health", "/api/auth")
        val authed = AuthMiddleware(authUseCases, publicPaths, okHandler)

        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        server.createContext("/", authed)
        server.executor = null
        server.start()
        port = server.address.port
    }

    @AfterEach
    fun tearDown() { server.stop(0) }

    @Test
    fun `public path bypasses auth`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/health")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
    }

    @Test
    fun `api auth path bypasses auth`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/auth/login")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
    }

    @Test
    fun `missing authorization returns 401`() {
        val request = HttpRequest.newBuilder().uri(URI("http://localhost:$port/api/workspaces/123")).GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(401, response.statusCode())
        assertTrue(response.body().contains("Unauthorized"))
    }

    @Test
    fun `invalid token returns 401`() {
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces/123"))
            .header("Authorization", "Bearer invalid-token")
            .GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(401, response.statusCode())
    }

    @Test
    fun `valid token passes through`() {
        authUseCases.register("test@test.com", "Test User", "password123")
        val token = authUseCases.login("test@test.com", "password123").getOrThrow()

        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces/123"))
            .header("Authorization", "Bearer $token")
            .GET().build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
    }

    private class InMemoryUserRepository : UserRepository {
        private val users = mutableMapOf<UUID, User>()
        override fun findById(id: UUID) = users[id]
        override fun findByEmail(email: String) = users.values.find { it.email == email }
        override fun save(user: User): User { users[user.id] = user; return user }
        override fun update(user: User): User { users[user.id] = user; return user }
        override fun delete(id: UUID) { users.remove(id) }
    }

    private class InMemorySessionRepository : SessionRepository {
        private val sessions = mutableMapOf<UUID, Session>()
        override fun findById(id: UUID) = sessions[id]
        override fun findByTokenHash(tokenHash: String) = sessions.values.find { it.tokenHash == tokenHash }
        override fun findActiveByUserId(userId: UUID) = sessions.values.filter { it.userId == userId && !it.isExpired }
        override fun save(session: Session): Session { sessions[session.id] = session; return session }
        override fun delete(id: UUID) { sessions.remove(id) }
        override fun deleteByUserId(userId: UUID) { sessions.entries.removeIf { it.value.userId == userId } }
    }
}
