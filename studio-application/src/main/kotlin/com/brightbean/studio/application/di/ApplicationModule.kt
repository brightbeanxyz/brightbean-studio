package com.brightbean.studio.application.di

import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.application.usecase.ConnectSocialAccountUseCase
import com.brightbean.studio.application.usecase.CreatePostUseCase
import com.brightbean.studio.application.usecase.CreateWorkspaceUseCase
import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.application.usecase.SchedulePostUseCase
import com.brightbean.studio.infrastructure.security.EncryptionService
import org.koin.dsl.module

val applicationModule = module {
    single { AuthUseCases(get(), get()) }
    single { CreateWorkspaceUseCase(get(), get()) }
    single { CreatePostUseCase(get(), get()) }
    single { SchedulePostUseCase(get(), get()) }
    single { PublishPostUseCase(get(), get(), get(), get()) }
    single {
        val encryptionService = get<EncryptionService>()
        ConnectSocialAccountUseCase(get(), get(), get(), { encryptionService.encrypt(it) }, { encryptionService.decrypt(it) })
    }
}
