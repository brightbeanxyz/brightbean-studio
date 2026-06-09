package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.Idea
import java.util.UUID

interface IdeaRepository {
    fun findById(id: UUID): Idea?
    fun findByWorkspaceId(workspaceId: UUID): List<Idea>
    fun findByGroupId(groupId: UUID): List<Idea>
    fun findByAuthorId(authorId: UUID): List<Idea>
    fun save(idea: Idea): Idea
    fun update(idea: Idea): Idea
    fun delete(id: UUID)
}
