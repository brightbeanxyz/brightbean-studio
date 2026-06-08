package com.brightbean.studio.infrastructure.di

import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import com.brightbean.studio.domain.repository.CredentialRepository
import com.brightbean.studio.domain.repository.InboxRepository
import com.brightbean.studio.domain.repository.MemberRepository
import com.brightbean.studio.domain.repository.OAuthConnectionRepository
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.PublishingQueueRepository
import com.brightbean.studio.domain.repository.SessionRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.domain.repository.UserRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import com.brightbean.studio.infrastructure.config.StudioConfig
import com.brightbean.studio.infrastructure.db.JDBIApprovalRequestRepository
import com.brightbean.studio.infrastructure.db.JDBICredentialRepository
import com.brightbean.studio.infrastructure.db.JDBIInboxRepository
import com.brightbean.studio.infrastructure.db.JDBIMemberRepository
import com.brightbean.studio.infrastructure.db.JDBIOAuthConnectionRepository
import com.brightbean.studio.infrastructure.db.JDBIPlatformPostRepository
import com.brightbean.studio.infrastructure.db.JDBIPostRepository
import com.brightbean.studio.infrastructure.db.JDBIPublishingQueueRepository
import com.brightbean.studio.infrastructure.db.JDBISessionRepository
import com.brightbean.studio.infrastructure.db.JDBISocialAccountRepository
import com.brightbean.studio.infrastructure.db.JDBIUserRepository
import com.brightbean.studio.infrastructure.db.JDBIWorkspaceRepository
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
    single<PublishingQueueRepository> { JDBIPublishingQueueRepository(get()) }
    single<PlatformPostRepository> { JDBIPlatformPostRepository(get()) }
    single<InboxRepository> { JDBIInboxRepository(get()) }
    single<ApprovalRequestRepository> { JDBIApprovalRequestRepository(get()) }
}

private fun createJdbi(config: StudioConfig): Jdbi {
    val jdbi = Jdbi.create(config.jdbcUrl)
    jdbi.installPlugin(KotlinPlugin())
    jdbi.installPlugin(KotlinSqlObjectPlugin())
    return jdbi
}
