package com.brightbean.studio.domain.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class ApprovalWorkflowTest {

    @Test
    fun `new approval workflow should be pending`() {
        val workflow = createApprovalWorkflow()
        
        assertTrue(workflow.isPending())
        assertFalse(workflow.isApproved())
        assertFalse(workflow.isRejected())
        assertFalse(workflow.isChangesRequested())
    }

    @Test
    fun `pending workflow can be approved`() {
        val workflow = createApprovalWorkflow()
        val reviewerId = UUID.randomUUID()
        val reviewedAt = Instant.now()

        val approved = workflow.approve(reviewerId, reviewedAt, "Looks good!")

        assertEquals(ApprovalStatus.APPROVED, approved.status)
        assertEquals(reviewerId, approved.reviewedBy)
        assertEquals(reviewedAt, approved.reviewedAt)
        assertEquals("Looks good!", approved.comment)
        assertTrue(approved.isApproved())
        assertFalse(approved.isPending())
    }

    @Test
    fun `pending workflow can be rejected`() {
        val workflow = createApprovalWorkflow()
        val reviewerId = UUID.randomUUID()
        val reviewedAt = Instant.now()

        val rejected = workflow.reject(reviewerId, reviewedAt, "Content violates guidelines")

        assertEquals(ApprovalStatus.REJECTED, rejected.status)
        assertEquals(reviewerId, rejected.reviewedBy)
        assertEquals(reviewedAt, rejected.reviewedAt)
        assertEquals("Content violates guidelines", rejected.comment)
        assertTrue(rejected.isRejected())
        assertFalse(rejected.isPending())
    }

    @Test
    fun `pending workflow can request changes`() {
        val workflow = createApprovalWorkflow()
        val reviewerId = UUID.randomUUID()
        val reviewedAt = Instant.now()

        val changesRequested = workflow.requestChanges(reviewerId, reviewedAt, "Please fix the caption")

        assertEquals(ApprovalStatus.CHANGES_REQUESTED, changesRequested.status)
        assertEquals(reviewerId, changesRequested.reviewedBy)
        assertEquals(reviewedAt, changesRequested.reviewedAt)
        assertEquals("Please fix the caption", changesRequested.comment)
        assertTrue(changesRequested.isChangesRequested())
        assertFalse(changesRequested.isPending())
    }

    private fun createApprovalWorkflow(
        id: UUID = UUID.randomUUID(),
        workspaceId: UUID = UUID.randomUUID(),
        postId: UUID = UUID.randomUUID(),
        requestedBy: UUID = UUID.randomUUID(),
    ): ApprovalWorkflow {
        return ApprovalWorkflow(
            id = id,
            workspaceId = workspaceId,
            postId = postId,
            requestedBy = requestedBy,
            requestedAt = Instant.now(),
            status = ApprovalStatus.PENDING,
            reviewedBy = null,
            reviewedAt = null,
            comment = null
        )
    }
}
