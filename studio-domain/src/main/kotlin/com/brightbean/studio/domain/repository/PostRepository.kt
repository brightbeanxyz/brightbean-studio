package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Post
import java.util.UUID

interface PostRepository {
    fun findById(id: UUID): Post?
    fun findByWorkspaceId(workspaceId: UUID): List<Post>
    fun findByAuthorId(authorId: UUID): List<Post>
    fun save(post: Post): Post
    fun update(post: Post): Post
    fun delete(id: UUID)
}
