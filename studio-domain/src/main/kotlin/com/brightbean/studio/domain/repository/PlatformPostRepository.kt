package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PlatformPost
import java.util.UUID

interface PlatformPostRepository {
    fun findById(id: UUID): PlatformPost?
    fun findByPostId(postId: UUID): List<PlatformPost>
    fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost>
    fun save(platformPost: PlatformPost): PlatformPost
    fun update(platformPost: PlatformPost): PlatformPost
    fun delete(id: UUID)
}
