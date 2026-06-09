package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PostingSlot
import com.brightbean.studio.domain.repository.PostingSlotRepository
import java.time.Instant
import java.time.LocalTime
import java.util.UUID

class PostingSlotUseCases(private val repository: PostingSlotRepository) {

    fun findByAccount(socialAccountId: UUID): List<PostingSlot> =
        repository.findBySocialAccountId(socialAccountId)

    fun findActiveByAccount(socialAccountId: UUID): List<PostingSlot> =
        repository.findActiveBySocialAccountId(socialAccountId)

    fun create(socialAccountId: UUID, dayOfWeek: Int, time: LocalTime): PostingSlot {
        val slot = PostingSlot(
            id = UUID.randomUUID(),
            socialAccountId = socialAccountId,
            dayOfWeek = dayOfWeek,
            time = time,
            isActive = true,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return repository.save(slot)
    }

    fun update(id: UUID, time: LocalTime): PostingSlot {
        val slot = repository.findById(id)
            ?: throw IllegalArgumentException("PostingSlot not found: $id")
        val updated = slot.copy(time = time, updatedAt = Instant.now())
        return repository.update(updated)
    }

    fun delete(id: UUID) {
        repository.delete(id)
    }

    fun toggleDay(socialAccountId: UUID, dayOfWeek: Int) {
        val slots = repository.findBySocialAccountId(socialAccountId)
            .filter { it.dayOfWeek == dayOfWeek }
        if (slots.isEmpty()) return
        val allActive = slots.all { it.isActive }
        val now = Instant.now()
        slots.forEach { slot ->
            repository.update(slot.copy(isActive = !allActive, updatedAt = now))
        }
    }
}
