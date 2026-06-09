package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PostComment
import java.util.UUID

interface PostCommentRepository {
    fun findByPostId(postId: UUID): List<PostComment>
    fun save(comment: PostComment): PostComment
    fun update(comment: PostComment): PostComment
    fun delete(id: UUID)
}
