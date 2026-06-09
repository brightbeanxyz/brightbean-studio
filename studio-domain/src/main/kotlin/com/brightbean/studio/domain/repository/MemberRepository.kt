package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Member
import java.util.UUID

interface MemberRepository {
    fun findById(id: UUID): Member?
    fun findByWorkspaceId(workspaceId: UUID): List<Member>
    fun findByUserId(userId: UUID): List<Member>
    fun save(member: Member): Member
    fun delete(id: UUID)
}
