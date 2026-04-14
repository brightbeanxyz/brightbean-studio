package com.brightbean.studio.web.server

import com.sun.net.httpserver.HttpHandler
import com.sun.net.httpserver.HttpServer
import java.net.InetSocketAddress

class BrightBeanServer(
    private val config: ServerConfig = ServerConfig(),
) {
    private var server: HttpServer? = null

    fun start() {
        server = HttpServer.create(InetSocketAddress(config.host, config.port), 0).apply {
            createContext("/health", HealthHandler())
            createContext("/", HealthHandler())
            executor = null
            start()
        }
    }

    fun stop() {
        server?.stop(1)
        server = null
    }
}
