package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.util.UUID

class ApprovePostUseCase(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {
    fun execute(postId: UUID) {
        postRepository.findById(postId)
            ?: throw IllegalArgumentException("Post not found: $postId")

        val platformPosts = platformPostRepository.findByPostId(postId)
        for (pp in platformPosts) {
            if (pp.status.canTransitionTo(PlatformPostStatus.APPROVED)) {
                val approved = pp.transitionTo(PlatformPostStatus.APPROVED)
                platformPostRepository.update(approved)
            }
        }
    }
}
