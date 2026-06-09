package com.brightbean.studio.domain.model

enum class PlatformPostStatus {
    DRAFT,
    PENDING_REVIEW,
    PENDING_CLIENT,
    APPROVED,
    CHANGES_REQUESTED,
    REJECTED,
    SCHEDULED,
    PUBLISHING,
    PARTIALLY_PUBLISHED,
    PUBLISHED,
    FAILED;

    companion object {
        private val VALID_TRANSITIONS: Map<PlatformPostStatus, Set<PlatformPostStatus>> = mapOf(
            DRAFT to setOf(PENDING_REVIEW, SCHEDULED, PUBLISHING),
            PENDING_REVIEW to setOf(APPROVED, CHANGES_REQUESTED, REJECTED),
            APPROVED to setOf(PENDING_CLIENT, SCHEDULED, PUBLISHING, DRAFT),
            PENDING_CLIENT to setOf(APPROVED, CHANGES_REQUESTED, REJECTED),
            CHANGES_REQUESTED to setOf(PENDING_REVIEW, DRAFT),
            REJECTED to setOf(DRAFT, PENDING_REVIEW),
            SCHEDULED to setOf(PUBLISHING, DRAFT),
            PUBLISHING to setOf(PUBLISHED, FAILED, SCHEDULED),
            FAILED to setOf(PUBLISHING, DRAFT, SCHEDULED),
            PUBLISHED to emptySet(),
        )
    }

    fun canTransitionTo(target: PlatformPostStatus): Boolean =
        VALID_TRANSITIONS[this]?.contains(target) == true

    fun transitionTo(target: PlatformPostStatus): PlatformPostStatus {
        if (!canTransitionTo(target)) {
            val allowed = VALID_TRANSITIONS[this] ?: emptySet()
            throw IllegalArgumentException("Invalid status transition: $this -> $target. Allowed: $allowed")
        }
        return target
    }

    val isEditable: Boolean
        get() = this in setOf(DRAFT, CHANGES_REQUESTED, REJECTED, APPROVED, SCHEDULED)

    val isSchedulable: Boolean
        get() = this in setOf(DRAFT, APPROVED)

    val isTerminal: Boolean
        get() = this == PUBLISHED
}

fun derivePostStatus(platformPostStatuses: Collection<PlatformPostStatus>): PlatformPostStatus {
    if (platformPostStatuses.isEmpty()) return PlatformPostStatus.DRAFT

    val unique = platformPostStatuses.toSet()
    if (unique.size == 1) return unique.first()

    val terminal = setOf(PlatformPostStatus.PUBLISHED, PlatformPostStatus.FAILED)
    if (unique.all { it in terminal }) {
        return when {
            unique.contains(PlatformPostStatus.PUBLISHED) && unique.contains(PlatformPostStatus.FAILED) -> PlatformPostStatus.PARTIALLY_PUBLISHED
            unique.contains(PlatformPostStatus.PUBLISHED) -> PlatformPostStatus.PUBLISHED
            else -> PlatformPostStatus.FAILED
        }
    }

    if (unique.contains(PlatformPostStatus.FAILED) && unique.any { it !in terminal }) {
        return PlatformPostStatus.PUBLISHING
    }

    val workflowOrder = listOf(
        PlatformPostStatus.DRAFT,
        PlatformPostStatus.CHANGES_REQUESTED,
        PlatformPostStatus.REJECTED,
        PlatformPostStatus.PENDING_REVIEW,
        PlatformPostStatus.PENDING_CLIENT,
        PlatformPostStatus.APPROVED,
        PlatformPostStatus.SCHEDULED,
        PlatformPostStatus.PUBLISHING,
        PlatformPostStatus.PARTIALLY_PUBLISHED,
        PlatformPostStatus.PUBLISHED,
    )
    return unique.minByOrNull { workflowOrder.indexOf(it).let { idx -> if (idx == -1) workflowOrder.size else idx } }
        ?: PlatformPostStatus.DRAFT
}
