package com.brightbean.studio.web.server

import com.brightbean.studio.web.api.CalendarApi
import com.brightbean.studio.web.api.CategoryApi
import com.brightbean.studio.web.api.CustomRoleApi
import com.brightbean.studio.web.api.FeedApi
import com.brightbean.studio.web.api.IdeaApi
import com.brightbean.studio.web.api.InvitationApi
import com.brightbean.studio.web.api.MemberApi
import com.brightbean.studio.web.api.MediaApi
import com.brightbean.studio.web.api.OrganizationApi
import com.brightbean.studio.web.api.PlatformConfigApi
import com.brightbean.studio.web.api.PlatformCredentialApi
import com.brightbean.studio.web.api.PlatformPostTransitionApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.TemplateApi
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
    private val platformConfigApi: PlatformConfigApi,
    private val platformCredentialApi: PlatformCredentialApi,
    private val categoryApi: CategoryApi,
    private val ideaApi: IdeaApi,
    private val templateApi: TemplateApi,
    private val feedApi: FeedApi,
    private val calendarApi: CalendarApi,
    private val platformPostTransitionApi: PlatformPostTransitionApi,
    private val mediaApi: MediaApi,
) : HttpHandler {
    private val postPattern = Regex("^/api/workspaces/[^/]+/posts|^/api/posts/[^/]+/(publish|schedule)")
    private val transitionPattern = Regex("^/api/workspaces/[^/]+/posts/[^/]+/platform-posts")
    private val categoryPattern = Regex("^/api/workspaces/[^/]+/categories")
    private val ideaPattern = Regex("^/api/workspaces/[^/]+/ideas|^/api/workspaces/[^/]+/idea-groups")
    private val templatePattern = Regex("^/api/workspaces/[^/]+/templates")
    private val feedPattern = Regex("^/api/workspaces/[^/]+/feeds")
    private val calendarPattern = Regex("^/api/workspaces/[^/]+/calendar|^/api/workspaces/[^/]+/queues|^/api/workspaces/[^/]+/posting-slots")
    private val socialAccountPattern = Regex("^/api/workspaces/[^/]+/social-accounts")
    private val mediaPattern = Regex("^/api/workspaces/[^/]+/media")
    private val invitationAcceptPattern = Regex("^/api/invitations")
    private val invitationPattern = Regex("^/api/orgs/[^/]+/invitations")
    private val memberPattern = Regex("^/api/orgs/[^/]+/members")
    private val rolePattern = Regex("^/api/orgs/[^/]+/roles")
    private val platformPattern = Regex("^/api/platforms")
    private val orgPattern = Regex("^/api/orgs")

    override fun handle(exchange: HttpExchange) {
        val path = exchange.requestURI.path
        when {
            transitionPattern.containsMatchIn(path) -> platformPostTransitionApi.handle(exchange)
            postPattern.containsMatchIn(path) -> postApi.handle(exchange)
            categoryPattern.containsMatchIn(path) -> categoryApi.handle(exchange)
            ideaPattern.containsMatchIn(path) -> ideaApi.handle(exchange)
            templatePattern.containsMatchIn(path) -> templateApi.handle(exchange)
            feedPattern.containsMatchIn(path) -> feedApi.handle(exchange)
            calendarPattern.containsMatchIn(path) -> calendarApi.handle(exchange)
            socialAccountPattern.containsMatchIn(path) -> socialAccountApi.handle(exchange)
            mediaPattern.containsMatchIn(path) -> mediaApi.handle(exchange)
            path.startsWith("/api/workspaces") -> workspaceApi.handle(exchange)
            invitationAcceptPattern.containsMatchIn(path) -> invitationApi.handle(exchange)
            invitationPattern.containsMatchIn(path) -> invitationApi.handle(exchange)
            memberPattern.containsMatchIn(path) -> memberApi.handle(exchange)
            rolePattern.containsMatchIn(path) -> customRoleApi.handle(exchange)
            platformPattern.containsMatchIn(path) -> platformConfigApi.handle(exchange)
            orgPattern.containsMatchIn(path) -> {
                if (path.contains("/credentials")) {
                    platformCredentialApi.handle(exchange)
                } else {
                    organizationApi.handle(exchange)
                }
            }
            else -> NotFoundHandler().handle(exchange)
        }
    }
}
