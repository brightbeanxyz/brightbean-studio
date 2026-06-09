package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.OnboardingChecklist
import java.util.UUID

interface OnboardingChecklistRepository {
    fun findByUserAndWorkspace(userId: UUID, workspaceId: UUID): OnboardingChecklist?
    fun save(checklist: OnboardingChecklist): OnboardingChecklist
    fun update(checklist: OnboardingChecklist): OnboardingChecklist
}
