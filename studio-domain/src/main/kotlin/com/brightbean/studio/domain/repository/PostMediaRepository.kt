package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PostMedia
import java.util.UUID

interface PostMediaRepository {
    fun findByPostId(postId: UUID): List<PostMedia>
    fun save(media: PostMedia): PostMedia
    fun delete(id: UUID)
    fun deleteByPostId(postId: UUID)
}
