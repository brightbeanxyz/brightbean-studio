package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.repository.SocialAccountRepository
import java.util.UUID

class DisconnectSocialAccountUseCase(
    private val socialAccountRepository: SocialAccountRepository,
) {
    fun execute(socialAccountId: UUID) {
        val socialAccount = socialAccountRepository.findById(socialAccountId)
            ?: throw IllegalArgumentException("Social account not found: $socialAccountId")

        val deactivatedAccount = socialAccount.copy(isActive = false)
        socialAccountRepository.update(deactivatedAccount)
    }
}