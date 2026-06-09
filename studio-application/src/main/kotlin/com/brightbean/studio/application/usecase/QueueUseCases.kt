package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.PostingSlot
import com.brightbean.studio.domain.model.Queue
import com.brightbean.studio.domain.model.QueueEntry
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.QueueEntryRepository
import com.brightbean.studio.domain.repository.QueueRepository
import com.brightbean.studio.domain.repository.PostingSlotRepository
import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneOffset
import java.util.UUID

class QueueUseCases(
    private val queueRepository: QueueRepository,
    private val queueEntryRepository: QueueEntryRepository,
    private val postingSlotRepository: PostingSlotRepository,
    private val postRepository: PostRepository,
    private val platformPostRepository: PlatformPostRepository,
) {

    fun list(workspaceId: UUID): List<Queue> =
        queueRepository.findByWorkspaceId(workspaceId)

    fun create(workspaceId: UUID, name: String, socialAccountId: UUID, categoryId: UUID?): Queue {
        val queue = Queue(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            name = name,
            categoryId = categoryId,
            socialAccountId = socialAccountId,
            isActive = true,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return queueRepository.save(queue)
    }

    fun delete(queueId: UUID) {
        queueEntryRepository.deleteByQueueId(queueId)
        queueRepository.delete(queueId)
    }

    fun getEntries(queueId: UUID): List<QueueEntry> =
        queueEntryRepository.findByQueueId(queueId)

    fun addToQueue(queueId: UUID, postId: UUID, priority: Boolean = false): QueueEntry {
        val queue = queueRepository.findById(queueId)
            ?: throw IllegalArgumentException("Queue not found: $queueId")

        val existing = queueEntryRepository.findByQueueId(queueId)
        val position = if (priority) {
            existing.forEach { entry ->
                queueEntryRepository.update(entry.copy(position = entry.position + 1))
            }
            0
        } else {
            existing.size
        }

        val entry = QueueEntry(
            id = UUID.randomUUID(),
            queueId = queueId,
            postId = postId,
            position = position,
            assignedSlotDatetime = null,
            createdAt = Instant.now(),
        )
        val saved = queueEntryRepository.save(entry)
        assignQueueSlots(queueId)
        return saved
    }

    fun reorder(queueId: UUID, orderedEntryIds: List<UUID>) {
        orderedEntryIds.forEachIndexed { index, entryId ->
            val entry = queueEntryRepository.findByQueueId(queueId)
                .find { it.id == entryId }
                ?: return@forEachIndexed
            queueEntryRepository.update(entry.copy(position = index))
        }
        assignQueueSlots(queueId)
    }

    private fun assignQueueSlots(queueId: UUID) {
        val queue = queueRepository.findById(queueId) ?: return
        val entries = queueEntryRepository.findByQueueId(queueId).sortedBy { it.position }
        val slots = postingSlotRepository.findActiveBySocialAccountId(queue.socialAccountId)
            .sortedWith(compareBy({ it.dayOfWeek }, { it.time }))

        if (slots.isEmpty() || entries.isEmpty()) return

        val slotDatetimes = generateSlotDatetimes(slots, entries.size, LocalDate.now())

        entries.forEachIndexed { index, entry ->
            val assigned = slotDatetimes.getOrNull(index)
            queueEntryRepository.update(entry.copy(assignedSlotDatetime = assigned))

            if (assigned != null) {
                platformPostRepository.findByPostId(entry.postId).forEach { pp ->
                    if (pp.status.canTransitionTo(PlatformPostStatus.SCHEDULED)) {
                        val scheduled = pp.transitionTo(PlatformPostStatus.SCHEDULED).copy(
                            scheduledAt = assigned,
                            updatedAt = Instant.now(),
                        )
                        platformPostRepository.update(scheduled)
                    } else if (pp.status == PlatformPostStatus.SCHEDULED) {
                        platformPostRepository.update(pp.copy(scheduledAt = assigned, updatedAt = Instant.now()))
                    }
                }
                val post = postRepository.findById(entry.postId)
                if (post != null) {
                    val allChildren = platformPostRepository.findByPostId(entry.postId)
                    val earliest = allChildren.mapNotNull { it.scheduledAt }.minByOrNull { it }
                    postRepository.update(post.copy(scheduledAt = earliest, updatedAt = Instant.now()))
                }
            }
        }
    }

    private fun generateSlotDatetimes(slots: List<PostingSlot>, count: Int, startDate: LocalDate): List<Instant> {
        val result = mutableListOf<Instant>()
        val maxDays = 60

        for (dayOffset in 0..maxDays) {
            val checkDate = startDate.plusDays(dayOffset.toLong())
            val djangoDow = checkDate.dayOfWeek.value - 1
            val matching = slots.filter { it.dayOfWeek == djangoDow }.sortedBy { it.time }
            for (slot in matching) {
                result.add(checkDate.atTime(slot.time).toInstant(ZoneOffset.UTC))
                if (result.size >= count) return result
            }
        }
        return result
    }
}
