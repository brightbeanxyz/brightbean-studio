package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.ConnectionLink
import com.brightbean.studio.domain.model.ConnectionLinkUsage
import com.brightbean.studio.domain.model.OnboardingChecklist
import com.brightbean.studio.domain.repository.ConnectionLinkRepository
import com.brightbean.studio.domain.repository.ConnectionLinkUsageRepository
import com.brightbean.studio.domain.repository.OnboardingChecklistRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIConnectionLinkRepository(jdbi: Jdbi) : ConnectionLinkRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: ConnectionLinkDao by lazy { jdbi.onDemand(ConnectionLinkDao::class.java) }

    override fun findById(id: UUID): ConnectionLink? = dao.findById(id)?.toDomain()
    override fun findByToken(token: String): ConnectionLink? = dao.findByToken(token)?.toDomain()
    override fun findByWorkspaceId(workspaceId: UUID): List<ConnectionLink> = dao.findByWorkspaceId(workspaceId).map { it.toDomain() }
    override fun save(link: ConnectionLink): ConnectionLink { dao.insert(link.toDto()); return link }
    override fun update(link: ConnectionLink): ConnectionLink { dao.update(link.toDto()); return link }

    private fun ConnectionLink.toDto() = ConnectionLinkDto(id, workspaceId, token, createdBy, expiresAt, revokedAt, createdAt)
    private fun ConnectionLinkDto.toDomain() = ConnectionLink(id, workspaceId, token, createdBy, expiresAt, revokedAt, createdAt)
}

class JDBIConnectionLinkUsageRepository(jdbi: Jdbi) : ConnectionLinkUsageRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: ConnectionLinkUsageDao by lazy { jdbi.onDemand(ConnectionLinkUsageDao::class.java) }

    override fun findByConnectionLinkId(connectionLinkId: UUID): List<ConnectionLinkUsage> = dao.findByConnectionLinkId(connectionLinkId).map { it.toDomain() }
    override fun save(usage: ConnectionLinkUsage): ConnectionLinkUsage { dao.insert(usage.toDto()); return usage }

    private fun ConnectionLinkUsage.toDto() = ConnectionLinkUsageDto(id, connectionLinkId, socialAccountId, connectedAt)
    private fun ConnectionLinkUsageDto.toDomain() = ConnectionLinkUsage(id, connectionLinkId, socialAccountId, connectedAt)
}

class JDBIOnboardingChecklistRepository(jdbi: Jdbi) : OnboardingChecklistRepository {
    init { jdbi.installPlugin(KotlinPlugin()); jdbi.installPlugin(KotlinSqlObjectPlugin()) }
    private val dao: OnboardingChecklistDao by lazy { jdbi.onDemand(OnboardingChecklistDao::class.java) }

    override fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): OnboardingChecklist? = dao.findByUserAndWorkspace(userId, workspaceId)?.toDomain()
    override fun save(checklist: OnboardingChecklist): OnboardingChecklist { dao.insert(checklist.toDto()); return checklist }
    override fun update(checklist: OnboardingChecklist): OnboardingChecklist { dao.update(checklist.toDto()); return checklist }

    private fun OnboardingChecklist.toDto() = OnboardingChecklistDto(id, userId, workspaceId, isDismissed, dismissedAt)
    private fun OnboardingChecklistDto.toDomain() = OnboardingChecklist(id, userId, workspaceId, isDismissed, dismissedAt)
}
