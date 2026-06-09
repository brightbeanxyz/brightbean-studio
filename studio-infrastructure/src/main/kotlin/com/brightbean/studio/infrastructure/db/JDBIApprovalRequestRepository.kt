package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.ApprovalRequest
import com.brightbean.studio.domain.model.ApprovalStatus
import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIApprovalRequestRepository(jdbi: Jdbi) : ApprovalRequestRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: ApprovalRequestDao by lazy { jdbi.onDemand(ApprovalRequestDao::class.java) }

    override fun findById(id: UUID): ApprovalRequest? =
        dao.findById(id)?.toDomain()

    override fun findByPostId(postId: UUID): List<ApprovalRequest> =
        dao.findByPostId(postId).map { it.toDomain() }

    override fun findByWorkspaceId(workspaceId: UUID): List<ApprovalRequest> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun save(approvalRequest: ApprovalRequest): ApprovalRequest {
        dao.insert(approvalRequest.toDto())
        return approvalRequest
    }

    override fun update(approvalRequest: ApprovalRequest): ApprovalRequest {
        dao.update(approvalRequest.toDto())
        return approvalRequest
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun ApprovalRequest.toDto() = ApprovalRequestDto(
        id = id,
        workspaceId = workspaceId,
        postId = postId,
        requestedBy = requestedBy,
        requestedAt = requestedAt,
        status = status.name,
        reviewedBy = reviewedBy,
        reviewedAt = reviewedAt,
        comment = comment,
    )

    private fun ApprovalRequestDto.toDomain() = ApprovalRequest(
        id = id,
        workspaceId = workspaceId,
        postId = postId,
        requestedBy = requestedBy,
        requestedAt = requestedAt,
        status = ApprovalStatus.valueOf(status),
        reviewedBy = reviewedBy,
        reviewedAt = reviewedAt,
        comment = comment,
    )
}
