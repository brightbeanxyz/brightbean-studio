package com.brightbean.studio.application.di

import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.application.usecase.CreateWorkspaceUseCase
import org.koin.dsl.module

val applicationModule = module {
    single { AuthUseCases(get(), get()) }
    single { CreateWorkspaceUseCase(get(), get()) }
}
