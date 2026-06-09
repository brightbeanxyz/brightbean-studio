package com.brightbean.studio.web.server

import com.brightbean.studio.application.auth.RbacContext
import com.brightbean.studio.application.auth.RbacResolver
import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.domain.model.OrgMembership
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.Session
import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.model.WorkspaceMembership
import com.brightbean.studio.domain.model.WorkspaceRole
import com.brightbean.studio.domain.repository.CustomRoleRepository
import com.brightbean.studio.domain.repository.OrgMembershipRepository
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.UserRepository
import com.brightbean.studio.domain.repository.WorkspaceMembershipRepository
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler
import com.sun.net.httpserver.HttpServer
import org.junit.jupiter.api.AfterEach
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
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

class RBACMiddlewareTest {

    private lateinit var server: HttpServer
    private var port: Int = 0
    private lateinit var userRepository: InMemoryUserRepository
    private lateinit var sessionRepository: InMemorySessionRepository
    private lateinit var orgMembershipRepository: InMemoryOrgMembershipRepository
    private lateinit var workspaceMembershipRepository: InMemoryWorkspaceMembershipRepository
    private lateinit var customRoleRepository: InMemoryCustomRoleRepository
    private lateinit var authUseCases: AuthUseCases
    private lateinit var rbacResolver: RbacResolver

    private val testUser = User(
        id = UUID.randomUUID(),
        email = "test@example.com",
        name = "Test User",
        passwordHash = "hash",
        isActive = true,
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    )
    private val testOrgId = UUID.randomUUID()
    private val testWorkspaceId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        userRepository = InMemoryUserRepository()
        sessionRepository = InMemorySessionRepository()
        orgMembershipRepository = InMemoryOrgMembershipRepository()
        workspaceMembershipRepository = InMemoryWorkspaceMembershipRepository()
        customRoleRepository = InMemoryCustomRoleRepository()
        authUseCases = AuthUseCases(userRepository, sessionRepository)
        rbacResolver = RbacResolver(orgMembershipRepository, workspaceMembershipRepository, customRoleRepository)

        userRepository.save(testUser)
        orgMembershipRepository.save(
            OrgMembership(
                id = UUID.randomUUID(),
                userId = testUser.id,
                organizationId = testOrgId,
                orgRole = OrgRole.OWNER,
                invitedAt = Instant.now(),
                acceptedAt = Instant.now(),
            )
        )
    }

    private fun startServer(capturingHandler: HttpHandler = CapturingHandler()) {
        val publicPaths = setOf("/health", "/api/auth")
        val middleware = RBACMiddleware(authUseCases, rbacResolver, publicPaths, capturingHandler)

        server = HttpServer.create(InetSocketAddress("localhost", 0), 0)
        server.createContext("/", middleware)
        server.executor = null
        server.start()
        port = server.address.port
    }

    @AfterEach
    fun tearDown() {
        server.stop(0)
    }

    @Test
    fun `public path bypasses RBAC`() {
        val handler = CapturingHandler()
        startServer(handler)

        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/health"))
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertNull(handler.capturedContext)
    }

    @Test
    fun `no auth header returns 401`() {
        startServer()

        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces"))
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(401, response.statusCode())
        assertTrue(response.body().contains("Missing or invalid Authorization header"))
    }

    @Test
    fun `invalid token returns 401`() {
        startServer()

        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces"))
            .header("Authorization", "Bearer invalid-token")
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(401, response.statusCode())
        assertTrue(response.body().contains("Invalid or expired session"))
    }

    @Test
    fun `valid token on non-workspace path passes with RbacContext`() {
        val handler = CapturingHandler()
        startServer(handler)

        val token = createSessionToken()

        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces"))
            .header("Authorization", "Bearer $token")
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertNotNull(handler.capturedContext)
        assertEquals("session-test@example.com", handler.capturedContext!!.user.email)
    }

    @Test
    fun `valid token with workspace membership passes`() {
        val token = createSessionToken()
        val sessionUser = authUseCases.verifySession(token)!!

        workspaceMembershipRepository.save(
            WorkspaceMembership(
                id = UUID.randomUUID(),
                userId = sessionUser.id,
                workspaceId = testWorkspaceId,
                workspaceRole = WorkspaceRole.OWNER,
                addedAt = Instant.now(),
            )
        )

        val handler = CapturingHandler()
        startServer(handler)

        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces/$testWorkspaceId/posts"))
            .header("Authorization", "Bearer $token")
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(200, response.statusCode())
        assertNotNull(handler.capturedContext)
        assertNotNull(handler.capturedContext!!.workspaceMembership)
    }

    @Test
    fun `valid token without workspace membership returns 403`() {
        val token = createSessionToken()
        val otherWorkspaceId = UUID.randomUUID()

        val handler = CapturingHandler()
        startServer(handler)

        val client = HttpClient.newHttpClient()
        val request = HttpRequest.newBuilder()
            .uri(URI("http://localhost:$port/api/workspaces/$otherWorkspaceId/posts"))
            .header("Authorization", "Bearer $token")
            .GET()
            .build()
        val response = client.send(request, HttpResponse.BodyHandlers.ofString())
        assertEquals(403, response.statusCode())
        assertTrue(response.body().contains("You do not have access to this workspace"))
    }

    private fun createSessionToken(): String {
        val email = "session-test@example.com"
        authUseCases.register(email, "Session Test", "password123")
        return authUseCases.login(email, "password123").getOrThrow()
    }

    private class CapturingHandler : HttpHandler {
        var capturedContext: RbacContext? = null

        override fun handle(exchange: HttpExchange) {
            capturedContext = exchange.getAttribute(RBACMiddleware.RBAC_CONTEXT_ATTR) as? RbacContext
            val response = """{"ok":true}"""
            exchange.responseHeaders.set("Content-Type", "application/json")
            exchange.sendResponseHeaders(200, response.toByteArray().size.toLong())
            exchange.responseBody.use { it.write(response.toByteArray()) }
        }
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

    private class InMemoryOrgMembershipRepository : OrgMembershipRepository {
        private val memberships = mutableMapOf<UUID, OrgMembership>()
        override fun findById(id: UUID) = memberships[id]
        override fun findByUserId(userId: UUID) = memberships.values.filter { it.userId == userId }
        override fun findByOrganizationId(organizationId: UUID) = memberships.values.filter { it.organizationId == organizationId }
        override fun findByUserAndOrganization(userId: UUID, organizationId: UUID) =
            memberships.values.find { it.userId == userId && it.organizationId == organizationId }
        override fun save(membership: OrgMembership): OrgMembership { memberships[membership.id] = membership; return membership }
        override fun update(membership: OrgMembership): OrgMembership { memberships[membership.id] = membership; return membership }
        override fun delete(id: UUID) { memberships.remove(id) }
    }

    private class InMemoryWorkspaceMembershipRepository : WorkspaceMembershipRepository {
        private val memberships = mutableMapOf<UUID, WorkspaceMembership>()
        override fun findById(id: UUID) = memberships[id]
        override fun findByUserId(userId: UUID) = memberships.values.filter { it.userId == userId }
        override fun findByWorkspaceId(workspaceId: UUID) = memberships.values.filter { it.workspaceId == workspaceId }
        override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID) =
            memberships.values.find { it.userId == userId && it.workspaceId == workspaceId }
        override fun save(membership: WorkspaceMembership): WorkspaceMembership { memberships[membership.id] = membership; return membership }
        override fun update(membership: WorkspaceMembership): WorkspaceMembership { memberships[membership.id] = membership; return membership }
        override fun delete(id: UUID) { memberships.remove(id) }
    }

    private class InMemoryCustomRoleRepository : CustomRoleRepository {
        private val roles = mutableMapOf<UUID, com.brightbean.studio.domain.model.CustomRole>()
        override fun findById(id: UUID) = roles[id]
        override fun findByOrganizationId(organizationId: UUID) = roles.values.filter { it.organizationId == organizationId }
        override fun save(customRole: com.brightbean.studio.domain.model.CustomRole): com.brightbean.studio.domain.model.CustomRole {
            roles[customRole.id] = customRole; return customRole
        }
        override fun update(customRole: com.brightbean.studio.domain.model.CustomRole): com.brightbean.studio.domain.model.CustomRole {
            roles[customRole.id] = customRole; return customRole
        }
        override fun delete(id: UUID) { roles.remove(id) }
    }
}
