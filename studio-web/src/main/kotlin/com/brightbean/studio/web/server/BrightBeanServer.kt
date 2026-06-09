package com.brightbean.studio.web.server

import com.brightbean.studio.application.auth.RbacResolver
import com.brightbean.studio.application.di.applicationModule
import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.infrastructure.di.infrastructureModule
import com.brightbean.studio.web.api.AuthApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.WorkspaceApi
import com.brightbean.studio.web.di.webModule
import com.sun.net.httpserver.HttpServer
import org.koin.core.component.KoinComponent
import org.koin.core.component.inject
import org.koin.core.context.startKoin
import java.net.InetSocketAddress

class BrightBeanServer(
    private val config: ServerConfig = ServerConfig(),
) : KoinComponent {
    private var server: HttpServer? = null
    private val authUseCases: AuthUseCases by inject()
    private val rbacResolver: RbacResolver by inject()
    private val authApi: AuthApi by inject()
    private val workspaceApi: WorkspaceApi by inject()
    private val postApi: PostApi by inject()
    private val socialAccountApi: SocialAccountApi by inject()

    fun start() {
        startKoin {
            modules(infrastructureModule, applicationModule, webModule)
        }

        val publicPaths = setOf("/health", "/api/auth")
        val router = Router(
            routes = mapOf(
                "/health" to HealthHandler(),
                "/api/auth" to authApi,
                "/api" to ApiDispatcher(postApi, socialAccountApi, workspaceApi),
            )
        )
        val authed = RBACMiddleware(authUseCases, rbacResolver, publicPaths, router)
        val rateLimited = RateLimitMiddleware(authed)
        val corsWrapped = Middleware.corsMiddleware(config.corsOrigins, rateLimited)
        val secured = SecurityHeadersMiddleware(corsWrapped)

        server = HttpServer.create(InetSocketAddress(config.host, config.port), 0).apply {
            createContext("/", secured)
            executor = null
            start()
        }
    }

    fun stop() {
        server?.stop(1)
        server = null
    }
}
