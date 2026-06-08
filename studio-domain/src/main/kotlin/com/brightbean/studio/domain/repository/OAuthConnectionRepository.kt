package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.OAuthConnection
import java.util.UUID

interface OAuthConnectionRepository {
    fun findById(id: UUID): OAuthConnection?
    fun findByUserIdAndProvider(userId: UUID, provider: String): OAuthConnection?
    fun findByProviderUser(provider: String, providerUserId: String): OAuthConnection?
    fun save(connection: OAuthConnection): OAuthConnection
    fun delete(id: UUID)
}
