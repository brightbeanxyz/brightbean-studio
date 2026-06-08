package com.brightbean.studio.web.api

import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.UserRepository
import com.google.gson.Gson
import com.sun.net.httpserver.HttpServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
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

class AuthApiTest {

    private lateinit var server: HttpServer
    private lateinit var client: HttpClient
    private var port: Int = 0
    private val gson = Gson()

    @BeforeEach
    fun setUp() {
        val userRepository = InMemoryUserRepository()
        val sessionRepository = InMemorySessionRepository()
        val authUseCases = AuthUseCases(userRepository, sessionRepository)
        val authApi = AuthApi(authUseCases)

        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        server.createContext("/api/auth", authApi)
        server.executor = null
        server.start()
        port = server.address.port

        client = HttpClient.newHttpClient()
    }

    @AfterEach
    fun tearDown() {
        server.stop(0)
    }

    @Test
    fun `register returns 201 with user`() {
        val body = """{"email":"test@example.com","name":"Test User","password":"password123"}"""
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/register"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(201, response.statusCode())
        assertTrue(response.body().contains("test@example.com"))
        assertTrue(response.body().contains("Test User"))
        assertTrue(response.body().contains("\"id\""))
    }

    @Test
    fun `register duplicate returns 409`() {
        val body = """{"email":"dup@example.com","name":"User 1","password":"password123"}"""
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/register"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .build()
        val first = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(201, first.statusCode())

        val body2 = """{"email":"dup@example.com","name":"User 2","password":"password456"}"""
        val request2 = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/register"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body2))
            .build()
        val second = client.send(request2, HttpResponse.BodyHandlers.ofString())
        assertEquals(409, second.statusCode())
        assertTrue(second.body().contains("already registered"))
    }

    @Test
    fun `login returns 200 with token`() {
        val registerBody = """{"email":"login@example.com","name":"Login User","password":"password123"}"""
        val registerRequest = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/register"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(registerBody))
            .build()
        client.send(registerRequest, HttpResponse.BodyHandlers.ofString())

        val loginBody = """{"email":"login@example.com","password":"password123"}"""
        val loginRequest = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/login"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(loginBody))
            .build()
        val response = client.send(loginRequest, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())

        val json = gson.fromJson(response.body(), Map::class.java)
        assertNotNull(json["token"])
        assertNotNull(json["user"])
    }

    @Test
    fun `login wrong password returns 401`() {
        val registerBody = """{"email":"wrong@example.com","name":"Wrong User","password":"password123"}"""
        val registerRequest = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/register"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(registerBody))
            .build()
        client.send(registerRequest, HttpResponse.BodyHandlers.ofString())

        val loginBody = """{"email":"wrong@example.com","password":"wrongpassword"}"""
        val loginRequest = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/auth/login"))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(loginBody))
            .build()
        val response = client.send(loginRequest, HttpResponse.BodyHandlers.ofString())
        assertEquals(401, response.statusCode())
        assertTrue(response.body().contains("Invalid credentials"))
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
