package com.brightbean.studio.infrastructure.di

import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.CustomRoleRepository
import com.brightbean.studio.domain.repository.InboxRepository
import com.brightbean.studio.domain.repository.InvitationRepository
import com.brightbean.studio.domain.repository.MemberRepository
import com.brightbean.studio.domain.repository.OAuthConnectionRepository
import com.brightbean.studio.domain.repository.OrgMembershipRepository
import com.brightbean.studio.domain.repository.OrganizationRepository
import com.brightbean.studio.domain.repository.AnalyticsPlatformConfigRepository
import com.brightbean.studio.domain.repository.PlatformCredentialRepository
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PlatformVisibilityRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.ContentCategoryRepository
import com.brightbean.studio.domain.repository.CSVImportJobRepository
import com.brightbean.studio.domain.repository.CustomCalendarEventRepository
import com.brightbean.studio.domain.repository.FeedRepository
import com.brightbean.studio.domain.repository.IdeaGroupRepository
import com.brightbean.studio.domain.repository.IdeaMediaRepository
import com.brightbean.studio.domain.repository.IdeaRepository
import com.brightbean.studio.domain.repository.PostingSlotRepository
import com.brightbean.studio.domain.repository.PostMediaRepository
import com.brightbean.studio.domain.repository.PostTemplateRepository
import com.brightbean.studio.domain.repository.PostVersionRepository
import com.brightbean.studio.domain.repository.QueueEntryRepository
import com.brightbean.studio.domain.repository.QueueRepository
import com.brightbean.studio.domain.repository.RecurrenceRuleRepository
import com.brightbean.studio.domain.repository.TagRepository
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.domain.repository.UserRepository
import com.brightbean.studio.domain.repository.WorkspaceMembershipRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import com.brightbean.studio.infrastructure.config.StudioConfig
import com.brightbean.studio.infrastructure.db.JDBIApprovalRequestRepository
import com.brightbean.studio.infrastructure.db.JDBICredentialRepository
import com.brightbean.studio.infrastructure.db.JDBICustomRoleRepository
import com.brightbean.studio.infrastructure.db.JDBIInboxRepository
import com.brightbean.studio.infrastructure.db.JDBIInvitationRepository
import com.brightbean.studio.infrastructure.db.JDBIMemberRepository
import com.brightbean.studio.infrastructure.db.JDBIOAuthConnectionRepository
import com.brightbean.studio.infrastructure.db.JDBIOrgMembershipRepository
import com.brightbean.studio.infrastructure.db.JDBIOrganizationRepository
import com.brightbean.studio.infrastructure.db.JDBIAnalyticsPlatformConfigRepository
import com.brightbean.studio.infrastructure.db.JDBIPlatformCredentialRepository
import com.brightbean.studio.infrastructure.db.JDBIPlatformPostRepository
import com.brightbean.studio.infrastructure.db.JDBIPlatformVisibilityRepository
import com.brightbean.studio.infrastructure.db.JDBIPostRepository
import com.brightbean.studio.infrastructure.db.JDBIContentCategoryRepository
import com.brightbean.studio.infrastructure.db.JDBICSVImportJobRepository
import com.brightbean.studio.infrastructure.db.JDBICustomCalendarEventRepository
import com.brightbean.studio.infrastructure.db.JDBIFeedRepository
import com.brightbean.studio.infrastructure.db.JDBIIdeaGroupRepository
import com.brightbean.studio.infrastructure.db.JDBIIdeaMediaRepository
import com.brightbean.studio.infrastructure.db.JDBIIdeaRepository
import com.brightbean.studio.infrastructure.db.JDBIPostingSlotRepository
import com.brightbean.studio.infrastructure.db.JDBIPostMediaRepository
import com.brightbean.studio.infrastructure.db.JDBIPostTemplateRepository
import com.brightbean.studio.infrastructure.db.JDBIPostVersionRepository
import com.brightbean.studio.infrastructure.db.JDBIQueueEntryRepository
import com.brightbean.studio.infrastructure.db.JDBIQueueRepository
import com.brightbean.studio.infrastructure.db.JDBIRecurrenceRuleRepository
import com.brightbean.studio.infrastructure.db.JDBITagRepository
import com.brightbean.studio.infrastructure.db.JDBISessionRepository
import com.brightbean.studio.infrastructure.db.JDBISocialAccountRepository
import com.brightbean.studio.infrastructure.db.JDBIUserRepository
import com.brightbean.studio.infrastructure.db.JDBIWorkspaceMembershipRepository
import com.brightbean.studio.infrastructure.db.JDBIWorkspaceRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.security.EncryptionService
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import org.koin.dsl.module

val infrastructureModule = module {
    single { StudioConfig.fromSystemEnv() }
    single { createJdbi(get()) }
    single<EncryptionService> { EncryptionService(get<StudioConfig>().secretKey, get<StudioConfig>().encryptionKeySalt) }
    single<UserRepository> { JDBIUserRepository(get()) }
    single<WorkspaceRepository> { JDBIWorkspaceRepository(get()) }
    single<OAuthConnectionRepository> { JDBIOAuthConnectionRepository(get()) }
    single<SessionRepository> { JDBISessionRepository(get()) }
    single<MemberRepository> { JDBIMemberRepository(get()) }
    single<CredentialRepository> { JDBICredentialRepository(get()) }
    single<SocialAccountRepository> { JDBISocialAccountRepository(get()) }
    single<PostRepository> { JDBIPostRepository(get()) }
    single<PlatformPostRepository> { JDBIPlatformPostRepository(get()) }
    single<ContentCategoryRepository> { JDBIContentCategoryRepository(get()) }
    single<TagRepository> { JDBITagRepository(get()) }
    single<IdeaRepository> { JDBIIdeaRepository(get()) }
    single<IdeaGroupRepository> { JDBIIdeaGroupRepository(get()) }
    single<IdeaMediaRepository> { JDBIIdeaMediaRepository(get()) }
    single<PostMediaRepository> { JDBIPostMediaRepository(get()) }
    single<PostVersionRepository> { JDBIPostVersionRepository(get()) }
    single<PostTemplateRepository> { JDBIPostTemplateRepository(get()) }
    single<CSVImportJobRepository> { JDBICSVImportJobRepository(get()) }
    single<FeedRepository> { JDBIFeedRepository(get()) }
    single<PostingSlotRepository> { JDBIPostingSlotRepository(get()) }
    single<QueueRepository> { JDBIQueueRepository(get()) }
    single<QueueEntryRepository> { JDBIQueueEntryRepository(get()) }
    single<RecurrenceRuleRepository> { JDBIRecurrenceRuleRepository(get()) }
    single<CustomCalendarEventRepository> { JDBICustomCalendarEventRepository(get()) }
    single<InboxRepository> { JDBIInboxRepository(get()) }
    single<ApprovalRequestRepository> { JDBIApprovalRequestRepository(get()) }
    single<OrganizationRepository> { JDBIOrganizationRepository(get()) }
    single<OrgMembershipRepository> { JDBIOrgMembershipRepository(get()) }
    single<WorkspaceMembershipRepository> { JDBIWorkspaceMembershipRepository(get()) }
    single<CustomRoleRepository> { JDBICustomRoleRepository(get()) }
    single<InvitationRepository> { JDBIInvitationRepository(get()) }
    single<PlatformCredentialRepository> { JDBIPlatformCredentialRepository(get()) }
    single<PlatformVisibilityRepository> { JDBIPlatformVisibilityRepository(get()) }
    single<AnalyticsPlatformConfigRepository> { JDBIAnalyticsPlatformConfigRepository(get()) }
    single { ProviderRegistry.from(emptyList()) }
}

private fun createJdbi(config: StudioConfig): Jdbi {
    val jdbi = Jdbi.create(config.jdbcUrl)
    jdbi.installPlugin(KotlinPlugin())
    jdbi.installPlugin(KotlinSqlObjectPlugin())
    return jdbi
}
