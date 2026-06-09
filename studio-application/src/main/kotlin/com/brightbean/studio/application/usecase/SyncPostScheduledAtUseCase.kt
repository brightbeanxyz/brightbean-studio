package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class SyncPostScheduledAtUseCase(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {
    fun execute(postId: UUID) {
        val post = postRepository.findById(postId) ?: return
        val children = platformPostRepository.findByPostId(postId)
        val earliest = children.mapNotNull { it.scheduledAt }.minByOrNull { it }
        val updated = post.copy(scheduledAt = earliest, updatedAt = Instant.now())
        postRepository.update(updated)
    }
}
