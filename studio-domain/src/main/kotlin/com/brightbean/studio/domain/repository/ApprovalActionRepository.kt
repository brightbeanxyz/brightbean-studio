package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.ApprovalAction
import java.util.UUID

interface ApprovalActionRepository {
    fun findByPostId(postId: UUID): List<ApprovalAction>
    fun save(action: ApprovalAction): ApprovalAction
}
