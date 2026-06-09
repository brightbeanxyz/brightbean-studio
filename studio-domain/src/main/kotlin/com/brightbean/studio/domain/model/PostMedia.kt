package com.brightbean.studio.domain.model

import java.util.UUID

data class PostMedia(
    val id: UUID,
    val postId: UUID,
    val mediaAssetId: UUID,
    val position: Int,
    val altText: String,
    val platformOverrides: String?,
)
