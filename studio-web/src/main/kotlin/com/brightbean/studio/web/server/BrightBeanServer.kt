package com.brightbean.studio.web.server

import com.brightbean.studio.application.auth.RbacResolver
import com.brightbean.studio.application.di.applicationModule
import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.infrastructure.di.infrastructureModule
import com.brightbean.studio.web.api.ApprovalApi
import com.brightbean.studio.web.api.AuthApi
import com.brightbean.studio.web.api.CalendarApi
import com.brightbean.studio.web.api.CategoryApi
import com.brightbean.studio.web.api.CustomRoleApi
import com.brightbean.studio.web.api.FeedApi
import com.brightbean.studio.web.api.IdeaApi
import com.brightbean.studio.web.api.InboxApi
import com.brightbean.studio.web.api.InvitationApi
import com.brightbean.studio.web.api.MemberApi
import com.brightbean.studio.web.api.MediaApi
import com.brightbean.studio.web.api.NotificationApi
import com.brightbean.studio.web.api.OrganizationApi
import com.brightbean.studio.web.api.PlatformConfigApi
import com.brightbean.studio.web.api.PlatformCredentialApi
import com.brightbean.studio.web.api.PlatformPostTransitionApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SettingsApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.TemplateApi
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
    private val invitationApi: InvitationApi by inject()
    private val memberApi: MemberApi by inject()
    private val organizationApi: OrganizationApi by inject()
    private val customRoleApi: CustomRoleApi by inject()
    private val platformConfigApi: PlatformConfigApi by inject()
    private val platformCredentialApi: PlatformCredentialApi by inject()
    private val categoryApi: CategoryApi by inject()
    private val ideaApi: IdeaApi by inject()
    private val templateApi: TemplateApi by inject()
    private val feedApi: FeedApi by inject()
    private val calendarApi: CalendarApi by inject()
    private val platformPostTransitionApi: PlatformPostTransitionApi by inject()
    private val mediaApi: MediaApi by inject()
    private val inboxApi: InboxApi by inject()
    private val approvalApi: ApprovalApi by inject()
    private val notificationApi: NotificationApi by inject()
    private val settingsApi: SettingsApi by inject()

    fun start() {
        startKoin {
            modules(infrastructureModule, applicationModule, webModule)
        }

        val publicPaths = setOf("/health", "/api/auth")
        val router = Router(
            routes = mapOf(
                "/health" to HealthHandler(),
                "/api/auth" to authApi,
                "/api" to ApiDispatcher(postApi, socialAccountApi, workspaceApi, invitationApi, memberApi, organizationApi, customRoleApi, platformConfigApi, platformCredentialApi, categoryApi, ideaApi, templateApi, feedApi, calendarApi, platformPostTransitionApi, mediaApi, inboxApi, approvalApi, notificationApi, settingsApi),
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
