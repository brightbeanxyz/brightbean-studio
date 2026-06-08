package com.brightbean.studio.web.server

import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.WorkspaceApi
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler

class ApiDispatcher(
    private val postApi: PostApi,
    private val socialAccountApi: SocialAccountApi,
    private val workspaceApi: WorkspaceApi,
) : HttpHandler {
    private val postPattern = Regex("^/api/workspaces/[^/]+/posts|^/api/posts/[^/]+/(publish|schedule)")
    private val socialAccountPattern = Regex("^/api/workspaces/[^/]+/social-accounts")

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        when {
            postPattern.containsMatchIn(path) -> postApi.handle(exchange)
            socialAccountPattern.containsMatchIn(path) -> socialAccountApi.handle(exchange)
            path.startsWith("/api/workspaces") -> workspaceApi.handle(exchange)
            else -> NotFoundHandler().handle(exchange)
        }
    }
}
