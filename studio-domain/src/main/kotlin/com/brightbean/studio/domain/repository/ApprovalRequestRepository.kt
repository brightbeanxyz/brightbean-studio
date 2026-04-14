package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ApprovalRequest
import java.util.UUID

interface ApprovalRequestRepository {
    fun findById(id: UUID): ApprovalRequest?
    fun findByPostId(postId: UUID): List<ApprovalRequest>
    fun findByWorkspaceId(workspaceId: UUID): List<ApprovalRequest>
    fun save(approvalRequest: ApprovalRequest): ApprovalRequest
    fun update(approvalRequest: ApprovalRequest): ApprovalRequest
    fun delete(id: UUID)
}
