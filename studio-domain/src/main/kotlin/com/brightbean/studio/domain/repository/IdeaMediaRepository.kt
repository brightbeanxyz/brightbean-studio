package com.brightbean.studio.domain.repository

import com.brightbean.studio.domain.model.IdeaMedia
import java.util.UUID

interface IdeaMediaRepository {
    fun findByIdeaId(ideaId: UUID): List<IdeaMedia>
    fun save(media: IdeaMedia): IdeaMedia
    fun deleteByIdeaId(ideaId: UUID)
    fun delete(id: UUID)
}
