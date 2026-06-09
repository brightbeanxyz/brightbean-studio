package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.PostingSlot
import java.util.UUID

interface PostingSlotRepository {
    fun findById(id: UUID): PostingSlot?
    fun findBySocialAccountId(socialAccountId: UUID): List<PostingSlot>
    fun findActiveBySocialAccountId(socialAccountId: UUID): List<PostingSlot>
    fun save(slot: PostingSlot): PostingSlot
    fun update(slot: PostingSlot): PostingSlot
    fun delete(id: UUID)
}
