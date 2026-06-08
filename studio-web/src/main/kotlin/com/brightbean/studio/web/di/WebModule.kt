package com.brightbean.studio.web.di

import com.brightbean.studio.web.api.AuthApi
import com.brightbean.studio.web.api.PostApi
import com.brightbean.studio.web.api.SocialAccountApi
import com.brightbean.studio.web.api.WorkspaceApi
import org.koin.dsl.module

val webModule = module {
    single { AuthApi(get()) }
    single { WorkspaceApi(get()) }
    single { PostApi(get(), get(), get(), get()) }
    single { SocialAccountApi(get(), get()) }
}
