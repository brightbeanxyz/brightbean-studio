package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.ApprovalAction
import com.brightbean.studio.domain.model.ApprovalActionType
import com.brightbean.studio.domain.model.ApprovalRequest
import com.brightbean.studio.domain.model.ApprovalStatus
import com.brightbean.studio.domain.repository.ApprovalActionRepository
import com.brightbean.studio.domain.repository.ApprovalRequestRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class ApprovalUseCasesTest {

    private lateinit var approvalRequestRepo: InMemApprovalRequestRepo
    private lateinit var approvalActionRepo: InMemApprovalActionRepo
    private lateinit var useCases: ApprovalUseCases

    @BeforeEach
    fun setUp() {
        approvalRequestRepo = InMemApprovalRequestRepo()
        approvalActionRepo = InMemApprovalActionRepo()
        useCases = ApprovalUseCases(approvalRequestRepo, approvalActionRepo)
    }

    @Test
    fun `submitForReview creates pending request`() {
        val workspaceId = UUID.randomUUID()
        val postId = UUID.randomUUID()
        val requestedBy = UUID.randomUUID()

        val request = useCases.submitForReview(workspaceId, postId, requestedBy)

        assertEquals(ApprovalStatus.PENDING, request.status)
        assertEquals(postId, request.postId)
        assertEquals(1, approvalActionRepo.actions.size)
        assertEquals(ApprovalActionType.SUBMITTED, approvalActionRepo.actions.first().action)
    }

    @Test
    fun `approve updates status and creates action`() {
        val request = createRequest()
        approvalRequestRepo.save(request)
        val reviewerId = UUID.randomUUID()

        val approved = useCases.approve(request.id, reviewerId, "Looks good")

        assertEquals(ApprovalStatus.APPROVED, approved.status)
        assertEquals(reviewerId, approved.reviewedBy)
        assertEquals(1, approvalActionRepo.actions.size)
        assertEquals(ApprovalActionType.APPROVED, approvalActionRepo.actions.first().action)
    }

    @Test
    fun `reject updates status`() {
        val request = createRequest()
        approvalRequestRepo.save(request)

        val rejected = useCases.reject(request.id, UUID.randomUUID(), "Bad content")
        assertEquals(ApprovalStatus.REJECTED, rejected.status)
    }

    @Test
    fun `requestChanges updates status`() {
        val request = createRequest()
        approvalRequestRepo.save(request)

        val changed = useCases.requestChanges(request.id, UUID.randomUUID(), "Fix title")
        assertEquals(ApprovalStatus.CHANGES_REQUESTED, changed.status)
    }

    @Test
    fun `resubmit resets to pending`() {
        val request = createRequest(status = ApprovalStatus.CHANGES_REQUESTED)
        approvalRequestRepo.save(request)

        val resubmitted = useCases.resubmit(request.id, UUID.randomUUID(), "Fixed")
        assertEquals(ApprovalStatus.PENDING, resubmitted.status)
        assertNull(resubmitted.reviewedBy)
    }

    @Test
    fun `bulkApprove approves multiple requests`() {
        val r1 = createRequest(); approvalRequestRepo.save(r1)
        val r2 = createRequest(); approvalRequestRepo.save(r2)
        val reviewerId = UUID.randomUUID()

        val results = useCases.bulkApprove(listOf(r1.id, r2.id), reviewerId)
        assertEquals(2, results.size)
        assertTrue(results.all { it.status == ApprovalStatus.APPROVED })
    }

    private fun createRequest(status: ApprovalStatus = ApprovalStatus.PENDING) = ApprovalRequest(
        id = UUID.randomUUID(),
        workspaceId = UUID.randomUUID(),
        postId = UUID.randomUUID(),
        requestedBy = UUID.randomUUID(),
        requestedAt = Instant.now(),
        status = status,
        reviewedBy = null,
        reviewedAt = null,
        comment = null,
    )

    class InMemApprovalRequestRepo : ApprovalRequestRepository {
        private val items = mutableMapOf<UUID, ApprovalRequest>()
        override fun findById(id: UUID) = items[id]
        override fun findByPostId(postId: UUID) = items.values.filter { it.postId == postId }
        override fun findByWorkspaceId(workspaceId: UUID) = items.values.filter { it.workspaceId == workspaceId }
        override fun save(r: ApprovalRequest) = r.also { items[r.id] = it }
        override fun update(r: ApprovalRequest) = r.also { items[r.id] = it }
        override fun delete(id: UUID) { items.remove(id) }
    }

    class InMemApprovalActionRepo : ApprovalActionRepository {
        val actions = mutableListOf<ApprovalAction>()
        override fun findByPostId(postId: UUID) = actions.filter { it.postId == postId }
        override fun save(a: ApprovalAction) = a.also { actions.add(it) }
    }
}
