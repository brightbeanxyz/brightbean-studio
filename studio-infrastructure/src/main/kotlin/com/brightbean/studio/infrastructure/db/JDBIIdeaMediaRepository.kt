package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.IdeaMedia
import com.brightbean.studio.domain.repository.IdeaMediaRepository
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import java.util.UUID

class JDBIIdeaMediaRepository(jdbi: Jdbi) : IdeaMediaRepository {

    init {
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())
    }

    private val dao: IdeaMediaDao by lazy { jdbi.onDemand(IdeaMediaDao::class.java) }

    override fun findByIdeaId(ideaId: UUID): List<IdeaMedia> =
        dao.findByIdeaId(ideaId).map { it.toDomain() }

    override fun save(media: IdeaMedia): IdeaMedia {
        dao.insert(media.toDto())
        return media
    }

    override fun deleteByIdeaId(ideaId: UUID) = dao.deleteByIdeaId(ideaId)

    override fun delete(id: UUID) = dao.delete(id)

    private fun IdeaMedia.toDto() = IdeaMediaDto(
        id = id, ideaId = ideaId, mediaAssetId = mediaAssetId, position = position,
        createdAt = createdAt, updatedAt = updatedAt,
    )

    private fun IdeaMediaDto.toDomain() = IdeaMedia(
        id = id, ideaId = ideaId, mediaAssetId = mediaAssetId, position = position,
        createdAt = createdAt, updatedAt = updatedAt,
    )
}
