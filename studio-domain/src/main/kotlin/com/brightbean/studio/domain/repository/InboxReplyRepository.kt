package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.InboxReply
import java.util.UUID

interface InboxReplyRepository {
    fun findByMessageId(inboxMessageId: UUID): List<InboxReply>
    fun save(reply: InboxReply): InboxReply
    fun delete(id: UUID)
}
