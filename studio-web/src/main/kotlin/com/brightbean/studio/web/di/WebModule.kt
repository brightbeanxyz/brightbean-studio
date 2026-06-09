package com.brightbean.studio.web.di

import com.brightbean.studio.web.api.ApprovalApi
import com.brightbean.studio.web.api.AuthApi
import com.brightbean.studio.web.api.CalendarApi
import com.brightbean.studio.web.api.CategoryApi
import com.brightbean.studio.web.api.CustomRoleApi
import com.brightbean.studio.web.api.FeedApi
import com.brightbean.studio.web.api.IdeaApi
import com.brightbean.studio.web.api.InboxApi
import com.brightbean.studio.web.api.InvitationApi
import com.brightbean.studio.web.api.MediaApi
import com.brightbean.studio.web.api.MemberApi
import com.brightbean.studio.web.api.NotificationApi
import com.brightbean.studio.web.api.OrganizationApi
import com.brightbean.studio.web.api.PlatformConfigApi
import com.brightbean.studio.web.api.PlatformCredentialApi
import com.brightbean.studio.web.api.PlatformPostTransitionApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.AnalyticsApi
import com.brightbean.studio.web.api.ApiKeyApi
import com.brightbean.studio.web.api.ClientPortalApi
import com.brightbean.studio.web.api.OnboardingApi
import com.brightbean.studio.web.api.SettingsApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.TemplateApi
import com.brightbean.studio.web.api.WorkspaceApi
import org.koin.dsl.module

val webModule = module {
    single { AuthApi(get()) }
    single { WorkspaceApi(get()) }
    single { PostApi(get(), get(), get(), get()) }
    single { SocialAccountApi(get(), get(), get(), get()) }
    single { InvitationApi(get(), get(), get(), get(), get()) }
    single { MemberApi(get(), get(), get(), get(), get(), get()) }
    single { OrganizationApi(get(), get(), get(), get()) }
    single { CustomRoleApi(get(), get(), get(), get()) }
    single { PlatformConfigApi() }
    single { PlatformCredentialApi(get()) }
    single { CategoryApi(get()) }
    single { IdeaApi(get(), get()) }
    single { TemplateApi(get()) }
    single { FeedApi(get()) }
    single { CalendarApi(get(), get(), get(), get()) }
    single { PlatformPostTransitionApi(get()) }
    single { MediaApi(get()) }
    single { InboxApi(get()) }
    single { ApprovalApi(get(), get()) }
    single { NotificationApi(get(), get()) }
    single { SettingsApi(get()) }
    single { AnalyticsApi(get()) }
    single { ClientPortalApi(get()) }
    single { OnboardingApi(get()) }
    single { ApiKeyApi(get()) }
}
