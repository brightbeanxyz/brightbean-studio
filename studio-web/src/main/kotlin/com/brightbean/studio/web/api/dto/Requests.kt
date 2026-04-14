package com.brightbean.studio.web.api.dto

import com.brightbean.studio.domain.model.PlatformType
import java.time.Instant
import java.util.UUID

data class CreatePostRequest(
    val content: String,
    val platforms: List<PlatformType>,
    val scheduledAt: Instant? = null,
    val requiresApproval: Boolean = false,
    val categoryId: UUID? = null,
    val tagIds: List<UUID> = emptyList(),
    val mediaIds: List<UUID> = emptyList(),
)

data class SchedulePostRequest(
    val scheduledFor: Instant,
)

data class ConnectSocialAccountRequest(
    val platformType: PlatformType,
    val authorizationCode: String,
)

data class ListPostsQuery(
    val page: Int = 1,
    val pageSize: Int = 25,
    val status: String? = null,
)
