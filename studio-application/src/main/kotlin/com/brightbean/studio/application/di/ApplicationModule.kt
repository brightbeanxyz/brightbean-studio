package com.brightbean.studio.application.di

import com.brightbean.studio.application.auth.RbacResolver
import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.application.usecase.ConnectSocialAccountUseCase
import com.brightbean.studio.application.usecase.CreateCustomRoleUseCase
import com.brightbean.studio.application.usecase.CreateOrganizationUseCase
import com.brightbean.studio.application.usecase.CreatePostUseCase
import com.brightbean.studio.application.usecase.AcceptInvitationUseCase
import com.brightbean.studio.application.usecase.CreateInvitationUseCase
import com.brightbean.studio.application.usecase.CreateWorkspaceUseCase
import com.brightbean.studio.application.usecase.DeleteCustomRoleUseCase
import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.application.usecase.RemoveMemberUseCase
import com.brightbean.studio.application.usecase.UpdateMemberOrgRoleUseCase
import com.brightbean.studio.application.usecase.UpdateWorkspaceAssignmentsUseCase
import com.brightbean.studio.application.usecase.ResendInvitationUseCase
import com.brightbean.studio.application.usecase.RevokeInvitationUseCase
import com.brightbean.studio.application.usecase.SchedulePostUseCase
import com.brightbean.studio.application.usecase.UpdateCustomRoleUseCase
import com.brightbean.studio.application.usecase.UpdateOrganizationUseCase
import com.brightbean.studio.infrastructure.security.EncryptionService
import org.koin.dsl.module

val applicationModule = module {
    single { RbacResolver(get(), get(), get()) }
    single { AuthUseCases(get(), get()) }
    single { CreateWorkspaceUseCase(get(), get()) }
    single { CreatePostUseCase(get(), get()) }
    single { SchedulePostUseCase(get(), get()) }
    single { PublishPostUseCase(get(), get(), get(), get()) }
    single {
        val encryptionService = get<EncryptionService>()
        ConnectSocialAccountUseCase(get(), get(), get(), { encryptionService.encrypt(it) }, { encryptionService.decrypt(it) })
    }
    single { CreateInvitationUseCase(get(), get(), get(), get()) }
    single { AcceptInvitationUseCase(get(), get(), get(), get()) }
    single { ResendInvitationUseCase(get(), get()) }
    single { RevokeInvitationUseCase(get(), get()) }
    single { CreateOrganizationUseCase(get(), get(), get(), get()) }
    single { UpdateOrganizationUseCase(get(), get()) }
    single { CreateCustomRoleUseCase(get(), get()) }
    single { UpdateCustomRoleUseCase(get(), get()) }
    single { DeleteCustomRoleUseCase(get(), get(), get()) }
    single { UpdateMemberOrgRoleUseCase(get()) }
    single { RemoveMemberUseCase(get(), get(), get()) }
    single { UpdateWorkspaceAssignmentsUseCase(get(), get(), get()) }
}
