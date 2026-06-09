package com.brightbean.studio.web.api.oauth

import com.brightbean.studio.domain.model.PlatformType

interface OAuthCallbackHandler {
    val platformType: PlatformType
    fun handleCallback(code: String, state: String, redirectUri: String): OAuthResult
}