package com.brightbean.studio.web.server

import com.brightbean.studio.web.api.CustomRoleApi
import com.brightbean.studio.web.api.InvitationApi
import com.brightbean.studio.web.api.MemberApi
import com.brightbean.studio.web.api.OrganizationApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.WorkspaceApi
import com.sun.net.httpserver.HttpExchange
import com.sun.net.httpserver.HttpHandler

class ApiDispatcher(
    private val postApi: PostApi,
    private val socialAccountApi: SocialAccountApi,
    private val workspaceApi: WorkspaceApi,
    private val invitationApi: InvitationApi,
    private val memberApi: MemberApi,
    private val organizationApi: OrganizationApi,
    private val customRoleApi: CustomRoleApi,
) : HttpHandler {
    private val postPattern = Regex("^/api/workspaces/[^/]+/posts|^/api/posts/[^/]+/(publish|schedule)")
    private val socialAccountPattern = Regex("^/api/workspaces/[^/]+/social-accounts")
    private val invitationAcceptPattern = Regex("^/api/invitations")
    private val invitationPattern = Regex("^/api/orgs/[^/]+/invitations")
    private val memberPattern = Regex("^/api/orgs/[^/]+/members")
    private val rolePattern = Regex("^/api/orgs/[^/]+/roles")
    private val orgPattern = Regex("^/api/orgs")

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        when {
            postPattern.containsMatchIn(path) -> postApi.handle(exchange)
            socialAccountPattern.containsMatchIn(path) -> socialAccountApi.handle(exchange)
            path.startsWith("/api/workspaces") -> workspaceApi.handle(exchange)
            invitationAcceptPattern.containsMatchIn(path) -> invitationApi.handle(exchange)
            invitationPattern.containsMatchIn(path) -> invitationApi.handle(exchange)
            memberPattern.containsMatchIn(path) -> memberApi.handle(exchange)
            rolePattern.containsMatchIn(path) -> customRoleApi.handle(exchange)
            orgPattern.containsMatchIn(path) -> organizationApi.handle(exchange)
            else -> NotFoundHandler().handle(exchange)
        }
    }
}
