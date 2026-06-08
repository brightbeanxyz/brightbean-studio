package com.brightbean.studio.infrastructure.db

import org.jdbi.v3.sqlobject.kotlin.RegisterKotlinMapper
import org.jdbi.v3.sqlobject.statement.SqlQuery
import org.jdbi.v3.sqlobject.statement.SqlUpdate
import java.util.UUID

@RegisterKotlinMapper(MemberDto::class)
interface MemberDao {
    @SqlQuery("SELECT * FROM member WHERE id = :id")
    fun findById(id: UUID): MemberDto?

    @SqlQuery("SELECT * FROM member WHERE workspace_id = :workspaceId")
    fun findByWorkspaceId(workspaceId: UUID): List<MemberDto>

    @SqlQuery("SELECT * FROM member WHERE user_id = :userId")
    fun findByUserId(userId: UUID): List<MemberDto>

    @SqlUpdate("INSERT INTO member (id, workspace_id, user_id, role, invited_by, joined_at) VALUES (:dto.id, :dto.workspaceId, :dto.userId, :dto.role, :dto.invitedBy, :dto.joinedAt)")
    fun insert(dto: MemberDto)

    @SqlUpdate("DELETE FROM member WHERE id = :id")
    fun delete(id: UUID)
}

data class MemberDto(
    val id: UUID,
    val workspaceId: UUID,
    val userId: UUID,
    val role: String,
    val invitedBy: UUID?,
    val joinedAt: java.time.Instant,
)
