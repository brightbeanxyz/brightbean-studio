package com.brightbean.studio.application.usecase

import com.brightbean.studio.application.service.NotificationEngine
import com.brightbean.studio.domain.model.Member
import com.brightbean.studio.domain.model.MemberRole
import com.brightbean.studio.domain.repository.MemberRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import java.time.Instant
import java.util.UUID

class InviteMemberUseCase(
    private val workspaceRepository: WorkspaceRepository,
    private val memberRepository: MemberRepository,
    private val notificationEngine: NotificationEngine,
) {
    fun execute(workspaceId: UUID, email: String, role: MemberRole, invitedBy: UUID): Member {
        val workspace = workspaceRepository.findById(workspaceId)
            ?: throw IllegalArgumentException("Workspace not found: $workspaceId")

        val member = Member(
            id = UUID.randomUUID(),
            workspaceId = workspace.id,
            userId = UUID.randomUUID(),
            role = role,
            invitedBy = invitedBy,
            joinedAt = Instant.now(),
        )
        memberRepository.save(member)
        notificationEngine.sendInvitation(email, workspaceId, invitedBy)

        return member
    }
}
