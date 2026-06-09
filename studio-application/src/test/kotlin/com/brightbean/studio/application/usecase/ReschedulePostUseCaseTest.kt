package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.util.UUID

class ReschedulePostUseCaseTest {

    private lateinit var postRepo: ReschedulePostInMemoryRepository
    private lateinit var platformPostRepo: ReschedulePlatformPostInMemoryRepository
    private lateinit var useCase: ReschedulePostUseCase

    @BeforeEach
    fun setUp() {
        postRepo = ReschedulePostInMemoryRepository()
        platformPostRepo = ReschedulePlatformPostInMemoryRepository()
        useCase = ReschedulePostUseCase(postRepo, platformPostRepo)
    }

    @Test
    fun `reschedule scheduled post`() {
        val postId = UUID.randomUUID()
        val originalTime = Instant.now().minusSeconds(3600)
        val newTime = Instant.now().plusSeconds(3600)
        saveTestPost(postId)
        val pp = saveTestPlatformPost(postId, PlatformPostStatus.SCHEDULED, originalTime)

        useCase.execute(pp.id, newTime)

        val updated = platformPostRepo.findById(pp.id)!!
        assertEquals(newTime, updated.scheduledAt)
    }

    @Test
    fun `reschedule draft post transitions to scheduled`() {
        val postId = UUID.randomUUID()
        val newTime = Instant.now().plusSeconds(3600)
        saveTestPost(postId)
        val pp = saveTestPlatformPost(postId, PlatformPostStatus.DRAFT, null)

        useCase.execute(pp.id, newTime)

        val updated = platformPostRepo.findById(pp.id)!!
        assertEquals(PlatformPostStatus.SCHEDULED, updated.status)
        assertEquals(newTime, updated.scheduledAt)
    }

    @Test
    fun `reject reschedule for published post`() {
        val postId = UUID.randomUUID()
        saveTestPost(postId)
        val pp = saveTestPlatformPost(postId, PlatformPostStatus.PUBLISHED, Instant.now())

        assertThrows<IllegalArgumentException> {
            useCase.execute(pp.id, Instant.now().plusSeconds(3600))
        }
    }

    private fun saveTestPost(postId: UUID): Post {
        val post = Post(
            id = postId,
            workspaceId = UUID.randomUUID(),
            authorId = null,
            title = "",
            caption = "",
            firstComment = "",
            internalNotes = "",
            tags = emptyList(),
            categoryId = null,
            scheduledAt = null,
            publishedAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return postRepo.save(post)
    }

    private fun saveTestPlatformPost(postId: UUID, status: PlatformPostStatus, scheduledAt: Instant?): PlatformPost {
        val pp = PlatformPost(
            id = UUID.randomUUID(),
            postId = postId,
            socialAccountId = UUID.randomUUID(),
            platformTitle = null,
            platformCaption = null,
            platformFirstComment = null,
            platformMedia = null,
            platformExtra = null,
            status = status,
            platformPostId = "",
            publishError = "",
            publishedAt = null,
            scheduledAt = scheduledAt,
            retryCount = 0,
            nextRetryAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        return platformPostRepo.save(pp)
    }
}

class ReschedulePostInMemoryRepository : PostRepository {
    private val items = mutableMapOf<UUID, Post>()
    override fun findById(id: UUID): Post? = items[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Post> = items.values.filter { it.workspaceId == workspaceId }
    override fun findByAuthorId(authorId: UUID): List<Post> = items.values.filter { it.authorId == authorId }
    override fun save(post: Post): Post { items[post.id] = post; return post }
    override fun update(post: Post): Post { items[post.id] = post; return post }
    override fun delete(id: UUID) { items.remove(id) }
}

class ReschedulePlatformPostInMemoryRepository : PlatformPostRepository {
    private val items = mutableMapOf<UUID, PlatformPost>()
    override fun findById(id: UUID): PlatformPost? = items[id]
    override fun findByPostId(postId: UUID): List<PlatformPost> = items.values.filter { it.postId == postId }
    override fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost> = items.values.filter { it.socialAccountId == socialAccountId }
    override fun findByStatus(status: PlatformPostStatus): List<PlatformPost> = items.values.filter { it.status == status }
    override fun findScheduledBefore(time: Instant): List<PlatformPost> = items.values.filter { it.scheduledAt != null && it.scheduledAt!! < time }
    override fun save(platformPost: PlatformPost): PlatformPost { items[platformPost.id] = platformPost; return platformPost }
    override fun update(platformPost: PlatformPost): PlatformPost { items[platformPost.id] = platformPost; return platformPost }
    override fun delete(id: UUID) { items.remove(id) }
}
