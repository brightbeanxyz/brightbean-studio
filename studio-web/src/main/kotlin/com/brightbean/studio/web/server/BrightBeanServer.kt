package com.brightbean.studio.web.server

import com.brightbean.studio.application.di.applicationModule
import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.infrastructure.di.infrastructureModule
import com.brightbean.studio.web.api.AuthApi
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

    fun start() {
        startKoin {
            modules(infrastructureModule, applicationModule, webModule)
        }

        val authApi = Middleware.corsMiddleware(config.corsOrigins, AuthApi(authUseCases))
        val healthHandler = Middleware.corsMiddleware(config.corsOrigins, HealthHandler())

        server = HttpServer.create(InetSocketAddress(config.host, config.port), 0).apply {
            createContext("/health", healthHandler)
            createContext("/", healthHandler)
            createContext("/api/auth", authApi)
            executor = null
            start()
        }
    }

    fun stop() {
        server?.stop(1)
        server = null
    }
}
