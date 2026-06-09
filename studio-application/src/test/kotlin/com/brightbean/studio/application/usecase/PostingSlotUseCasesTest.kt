package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PostingSlot
import com.brightbean.studio.domain.repository.PostingSlotRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.time.LocalTime
import java.util.UUID

class PostingSlotUseCasesTest {

    private lateinit var repository: PostingSlotInMemoryRepository
    private lateinit var useCases: PostingSlotUseCases

    @BeforeEach
    fun setUp() {
        repository = PostingSlotInMemoryRepository()
        useCases = PostingSlotUseCases(repository)
    }

    @Test
    fun `create slot`() {
        val accountId = UUID.randomUUID()
        val slot = useCases.create(accountId, 1, LocalTime.of(9, 0))

        assertEquals(accountId, slot.socialAccountId)
        assertEquals(1, slot.dayOfWeek)
        assertEquals(LocalTime.of(9, 0), slot.time)
        assertTrue(slot.isActive)
        assertNotNull(slot.id)
    }

    @Test
    fun `update slot time`() {
        val accountId = UUID.randomUUID()
        val created = useCases.create(accountId, 1, LocalTime.of(9, 0))

        val updated = useCases.update(created.id, LocalTime.of(10, 30))

        assertEquals(LocalTime.of(10, 30), updated.time)
        assertEquals(created.id, updated.id)
    }

    @Test
    fun `delete slot`() {
        val accountId = UUID.randomUUID()
        val created = useCases.create(accountId, 1, LocalTime.of(9, 0))

        useCases.delete(created.id)

        assertNull(repository.findById(created.id))
    }

    @Test
    fun `toggle day deactivates all active slots`() {
        val accountId = UUID.randomUUID()
        useCases.create(accountId, 1, LocalTime.of(9, 0))
        useCases.create(accountId, 1, LocalTime.of(12, 0))

        useCases.toggleDay(accountId, 1)

        val slots = useCases.findByAccount(accountId).filter { it.dayOfWeek == 1 }
        assertTrue(slots.all { !it.isActive })
    }
}

class PostingSlotInMemoryRepository : PostingSlotRepository {
    private val slots = mutableMapOf<UUID, PostingSlot>()

    override fun findById(id: UUID): PostingSlot? = slots[id]
    override fun findBySocialAccountId(socialAccountId: UUID): List<PostingSlot> =
        slots.values.filter { it.socialAccountId == socialAccountId }
    override fun findActiveBySocialAccountId(socialAccountId: UUID): List<PostingSlot> =
        slots.values.filter { it.socialAccountId == socialAccountId && it.isActive }
    override fun save(slot: PostingSlot): PostingSlot { slots[slot.id] = slot; return slot }
    override fun update(slot: PostingSlot): PostingSlot { slots[slot.id] = slot; return slot }
    override fun delete(id: UUID) { slots.remove(id) }
}
