package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PostVersion
import java.util.UUID

interface PostVersionRepository {
    fun findByPostId(postId: UUID): List<PostVersion>
    fun findLatestByPostId(postId: UUID): PostVersion?
    fun save(version: PostVersion): PostVersion
}
