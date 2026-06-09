package com.brightbean.studio.web.di

import com.brightbean.studio.web.api.AuthApi
import com.brightbean.studio.web.api.CustomRoleApi
import com.brightbean.studio.web.api.InvitationApi
import com.brightbean.studio.web.api.MemberApi
import com.brightbean.studio.web.api.OrganizationApi
import com.brightbean.studio.web.api.PlatformConfigApi
import com.brightbean.studio.web.api.PlatformCredentialApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SocialAccountApi
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
}
