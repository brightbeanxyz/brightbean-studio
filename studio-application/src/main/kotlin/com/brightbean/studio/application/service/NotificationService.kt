package com.brightbean.studio.application.service

import java.util.UUID

interface NotificationService {
    fun sendInvitation(email: String, workspaceId: UUID, inviterId: UUID)
}
