package com.brightbean.studio.application.di

import com.brightbean.studio.application.auth.RbacResolver
import com.brightbean.studio.application.usecase.AuthUseCases
import com.brightbean.studio.application.usecase.CheckSocialAccountHealthUseCase
import com.brightbean.studio.application.usecase.ConnectSocialAccountUseCase
import com.brightbean.studio.application.usecase.ContentCategoryUseCases
import com.brightbean.studio.application.usecase.CreateCustomRoleUseCase
import com.brightbean.studio.application.usecase.CreateOrganizationUseCase
import com.brightbean.studio.application.usecase.CreatePostUseCase
import com.brightbean.studio.application.usecase.AcceptInvitationUseCase
import com.brightbean.studio.application.usecase.CreateInvitationUseCase
import com.brightbean.studio.application.usecase.CreateWorkspaceUseCase
import com.brightbean.studio.application.usecase.DeleteCustomRoleUseCase
import com.brightbean.studio.application.usecase.IdeaGroupUseCases
import com.brightbean.studio.application.usecase.IdeaUseCases
import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.application.usecase.ReconnectSocialAccountUseCase
import com.brightbean.studio.application.usecase.RemoveMemberUseCase
import com.brightbean.studio.application.usecase.UpdateMemberOrgRoleUseCase
import com.brightbean.studio.application.usecase.UpdateWorkspaceAssignmentsUseCase
import com.brightbean.studio.application.usecase.ResendInvitationUseCase
import com.brightbean.studio.application.usecase.RevokeInvitationUseCase
import com.brightbean.studio.application.usecase.SavePostVersionUseCase
import com.brightbean.studio.application.usecase.SchedulePostUseCase
import com.brightbean.studio.application.usecase.SyncPostScheduledAtUseCase
import com.brightbean.studio.application.usecase.TransitionPlatformPostUseCase
import com.brightbean.studio.application.usecase.ApprovePostUseCase
import com.brightbean.studio.application.usecase.UpdateCustomRoleUseCase
import com.brightbean.studio.application.usecase.UpdateOrganizationUseCase
import com.brightbean.studio.application.usecase.PostingSlotUseCases
import com.brightbean.studio.application.usecase.QueueUseCases
import com.brightbean.studio.application.usecase.CustomCalendarEventUseCases
import com.brightbean.studio.application.usecase.ReschedulePostUseCase
import com.brightbean.studio.application.usecase.PostTemplateUseCases
import com.brightbean.studio.application.usecase.FeedUseCases
import com.brightbean.studio.application.usecase.MediaLibraryUseCases
import com.brightbean.studio.infrastructure.security.EncryptionService
import org.koin.dsl.module

val applicationModule = module {
    single { RbacResolver(get(), get(), get()) }
    single { AuthUseCases(get(), get()) }
    single { CreateWorkspaceUseCase(get(), get()) }
    single { CreatePostUseCase(get(), get(), get()) }
    single { SchedulePostUseCase(get(), get()) }
    single { ApprovePostUseCase(get(), get()) }
    single { PublishPostUseCase(get(), get(), get(), get()) }
    single { TransitionPlatformPostUseCase(get(), get()) }
    single { SyncPostScheduledAtUseCase(get(), get()) }
    single { SavePostVersionUseCase(get(), get(), get()) }
    single { ContentCategoryUseCases(get()) }
    single { IdeaUseCases(get(), get(), get(), get(), get(), get()) }
    single { IdeaGroupUseCases(get()) }
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
    single { CheckSocialAccountHealthUseCase(get(), get(), get()) }
    single {
        val encryptionService = get<EncryptionService>()
        ReconnectSocialAccountUseCase(get(), get(), get(), { encryptionService.encrypt(it) })
    }
    single { PostingSlotUseCases(get()) }
    single { QueueUseCases(get(), get(), get(), get(), get()) }
    single { CustomCalendarEventUseCases(get()) }
    single { ReschedulePostUseCase(get(), get()) }
    single { PostTemplateUseCases(get()) }
    single { FeedUseCases(get()) }
    single { MediaLibraryUseCases(get(), get(), get()) }
}
