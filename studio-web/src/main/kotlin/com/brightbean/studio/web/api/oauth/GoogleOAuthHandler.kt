package com.brightbean.studio.web.api.oauth

import com.brightbean.studio.application.usecase.ConnectSocialAccountUseCase
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.repository.SocialAccountRepository
import java.util.UUID

class GoogleOAuthHandler(
    private val connectSocialAccountUseCase: ConnectSocialAccountUseCase,
    private val socialAccountRepository: SocialAccountRepository,
) : OAuthCallbackHandler {

    override val platformType: PlatformType = PlatformType.GOOGLE_BUSINESS

    override fun handleCallback(code: String, state: String, redirectUri: String): OAuthResult {
        val workspaceId = UUID.fromString(state)

        val socialAccount = connectSocialAccountUseCase.execute(
            workspaceId = workspaceId,
            platformType = platformType,
            authorizationCode = code,
        )

        return OAuthResult(
            socialAccountId = socialAccount.id,
            workspaceId = socialAccount.workspaceId,
            platformUserId = socialAccount.platformUserId,
            username = socialAccount.platformUsername,
        )
    }
}