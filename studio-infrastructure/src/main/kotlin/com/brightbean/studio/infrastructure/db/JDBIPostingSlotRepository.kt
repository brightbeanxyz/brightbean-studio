package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.PostingSlot
import com.brightbean.studio.domain.repository.PostingSlotRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIPostingSlotRepository(jdbi: Jdbi) : PostingSlotRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: PostingSlotDao by lazy { jdbi.onDemand(PostingSlotDao::class.java) }

    override fun findById(id: UUID): PostingSlot? = dao.findById(id)?.toDomain()

    override fun findBySocialAccountId(socialAccountId: UUID): List<PostingSlot> =
        dao.findBySocialAccountId(socialAccountId).map { it.toDomain() }

    override fun findActiveBySocialAccountId(socialAccountId: UUID): List<PostingSlot> =
        dao.findActiveBySocialAccountId(socialAccountId).map { it.toDomain() }

    override fun save(slot: PostingSlot): PostingSlot {
        dao.insert(slot.toDto())
        return slot
    }

    override fun update(slot: PostingSlot): PostingSlot {
        dao.update(slot.toDto())
        return slot
    }

    override fun delete(id: UUID) = dao.delete(id)

    private fun PostingSlot.toDto() = PostingSlotDto(
        id = id, socialAccountId = socialAccountId, dayOfWeek = dayOfWeek,
        time = time, isActive = isActive, createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun PostingSlotDto.toDomain() = PostingSlot(
        id = id, socialAccountId = socialAccountId, dayOfWeek = dayOfWeek,
        time = time, isActive = isActive, createdAt = createdAt, updatedAt = updatedAt,
    )
}
