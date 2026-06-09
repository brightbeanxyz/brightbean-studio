package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PostVersion
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostMediaRepository
import com.brightbean.studio.domain.repository.PostVersionRepository
import com.google.gson.Gson
import java.time.Instant
import java.util.UUID

class SavePostVersionUseCase(
    private val postVersionRepository: PostVersionRepository,
    private val platformPostRepository: PlatformPostRepository,
    private val postMediaRepository: PostMediaRepository,
) {
    private val gson = Gson()

    fun execute(postId: UUID, createdBy: UUID?): PostVersion {
        val existing = postVersionRepository.findByPostId(postId)
        val nextVersion = (existing.maxOfOrNull { it.versionNumber } ?: 0) + 1

        val children = platformPostRepository.findByPostId(postId)
        val media = postMediaRepository.findByPostId(postId)

        val snapshot = mapOf(
            "platformPosts" to children.map { mapOf(
                "id" to it.id.toString(),
                "socialAccountId" to it.socialAccountId.toString(),
                "status" to it.status.name,
                "platformCaption" to it.platformCaption,
                "scheduledAt" to it.scheduledAt?.toString(),
            )},
            "media" to media.map { mapOf(
                "id" to it.id.toString(),
                "mediaAssetId" to it.mediaAssetId.toString(),
                "position" to it.position,
            )},
        )

        val version = PostVersion(
            id = UUID.randomUUID(),
            postId = postId,
            versionNumber = nextVersion,
            snapshot = gson.toJson(snapshot),
            createdBy = createdBy,
            createdAt = Instant.now(),
        )
        return postVersionRepository.save(version)
    }
}
