package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import java.time.Instant
import java.util.UUID

class ReschedulePostUseCase(
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {
    fun execute(platformPostId: UUID, newDatetime: Instant) {
        val pp = platformPostRepository.findById(platformPostId)
            ?: throw IllegalArgumentException("PlatformPost not found: $platformPostId")

        if (pp.status !in setOf(PlatformPostStatus.DRAFT, PlatformPostStatus.APPROVED, PlatformPostStatus.SCHEDULED)) {
            throw IllegalArgumentException("Cannot reschedule platform post in status: ${pp.status}")
        }

        val updated = if (pp.status == PlatformPostStatus.DRAFT) {
            pp.transitionTo(PlatformPostStatus.SCHEDULED).copy(
                scheduledAt = newDatetime,
                updatedAt = Instant.now(),
            )
        } else {
            pp.copy(scheduledAt = newDatetime, updatedAt = Instant.now())
        }
        platformPostRepository.update(updated)

        val allChildren = platformPostRepository.findByPostId(pp.postId)
        val earliest = allChildren.mapNotNull { it.scheduledAt }.minByOrNull { it }
        val post = postRepository.findById(pp.postId)
        if (post != null) {
            postRepository.update(post.copy(scheduledAt = earliest, updatedAt = Instant.now()))
        }
    }

    fun executeByPost(postId: UUID, newDatetime: Instant) {
        val platformPosts = platformPostRepository.findByPostId(postId)
        for (pp in platformPosts) {
            if (pp.status in setOf(PlatformPostStatus.DRAFT, PlatformPostStatus.APPROVED, PlatformPostStatus.SCHEDULED)) {
                val updated = if (pp.status == PlatformPostStatus.DRAFT) {
                    pp.transitionTo(PlatformPostStatus.SCHEDULED).copy(
                        scheduledAt = newDatetime,
                        updatedAt = Instant.now(),
                    )
                } else {
                    pp.copy(scheduledAt = newDatetime, updatedAt = Instant.now())
                }
                platformPostRepository.update(updated)
            }
        }
        val post = postRepository.findById(postId)
        if (post != null) {
            postRepository.update(post.copy(scheduledAt = newDatetime, updatedAt = Instant.now()))
        }
    }
}
