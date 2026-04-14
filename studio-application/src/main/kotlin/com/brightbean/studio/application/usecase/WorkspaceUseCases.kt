package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Member
import com.brightbean.studio.domain.model.MemberRole
import com.brightbean.studio.domain.model.Workspace
import com.brightbean.studio.domain.model.WorkspaceSettings
import com.brightbean.studio.domain.repository.MemberRepository
import com.brightbean.studio.domain.repository.WorkspaceRepository
import java.time.Instant
import java.util.UUID

class CreateWorkspaceUseCase(
    private val workspaceRepository: WorkspaceRepository,
    private val memberRepository: MemberRepository,
) {
    fun execute(name: String, slug: String, ownerId: UUID): Workspace {
        val now = Instant.now()
        val workspace = Workspace(
            id = UUID.randomUUID(),
            name = name,
            slug = slug,
            ownerId = ownerId,
            settings = WorkspaceSettings(),
            createdAt = now,
            updatedAt = now,
        )
        workspaceRepository.save(workspace)

        val ownerMember = Member(
            id = UUID.randomUUID(),
            workspaceId = workspace.id,
            userId = ownerId,
            role = MemberRole.OWNER,
            invitedBy = null,
            joinedAt = now,
        )
        memberRepository.save(ownerMember)

        return workspace
    }
}
