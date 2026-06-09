package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.InternalNote
import java.util.UUID

interface InternalNoteRepository {
    fun findByMessageId(inboxMessageId: UUID): List<InternalNote>
    fun save(note: InternalNote): InternalNote
    fun delete(id: UUID)
}
