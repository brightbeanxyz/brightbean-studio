package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.Member
import com.brightbean.studio.domain.model.MemberRole
import com.brightbean.studio.domain.repository.MemberRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIMemberRepository(jdbi: Jdbi) : MemberRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: MemberDao by lazy { jdbi.onDemand(MemberDao::class.java) }

    override fun findById(id: UUID): Member? =
        dao.findById(id)?.toDomain()

    override fun findByWorkspaceId(workspaceId: UUID): List<Member> =
        dao.findByWorkspaceId(workspaceId).map { it.toDomain() }

    override fun findByUserId(userId: UUID): List<Member> =
        dao.findByUserId(userId).map { it.toDomain() }

    override fun save(member: Member): Member {
        dao.insert(member.toDto())
        return member
    }

    override fun delete(id: UUID) {
        dao.delete(id)
    }

    private fun Member.toDto() = MemberDto(
        id = id,
        workspaceId = workspaceId,
        userId = userId,
        role = role.name,
        invitedBy = invitedBy,
        joinedAt = joinedAt,
    )

    private fun MemberDto.toDomain() = Member(
        id = id,
        workspaceId = workspaceId,
        userId = userId,
        role = MemberRole.valueOf(role),
        invitedBy = invitedBy,
        joinedAt = joinedAt,
    )
}
