package com.brightbean.studio.domain.model

import java.time.Instant
import java.util.UUID

data class PlatformPost(
    val id: UUID,
    val postId: UUID,
    val socialAccountId: UUID,
    val platformTitle: String?,
    val platformCaption: String?,
    val platformFirstComment: String?,
    val platformMedia: String?,
    val platformExtra: String?,
    val status: PlatformPostStatus,
    val platformPostId: String,
    val publishError: String,
    val publishedAt: Instant?,
    val scheduledAt: Instant?,
    val retryCount: Int,
    val nextRetryAt: Instant?,
    val createdAt: Instant,
    val updatedAt: Instant,
) {
    fun canTransitionTo(target: PlatformPostStatus): Boolean =
        status.canTransitionTo(target)

    fun transitionTo(target: PlatformPostStatus): PlatformPost {
        status.transitionTo(target)
        return copy(
            status = target,
            publishedAt = if (target == PlatformPostStatus.PUBLISHED) Instant.now() else publishedAt,
            updatedAt = Instant.now(),
        )
    }

    fun effectiveCaption(baseCaption: String): String =
        platformCaption ?: baseCaption

    fun effectiveTitle(baseTitle: String): String =
        platformTitle ?: baseTitle

    fun effectiveFirstComment(baseFirstComment: String): String =
        platformFirstComment ?: baseFirstComment

    val isEditable: Boolean get() = status.isEditable
    val isSchedulable: Boolean get() = status.isSchedulable
}
