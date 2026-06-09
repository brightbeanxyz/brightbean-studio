package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.util.UUID

class TransitionPlatformPostUseCaseTest {

    private lateinit var postRepository: PostRepository
    private lateinit var platformPostRepository: PlatformPostRepository
    private lateinit var useCase: TransitionPlatformPostUseCase

    @BeforeEach
    fun setUp() {
        postRepository = TransitionInMemoryPostRepository()
        platformPostRepository = TransitionInMemoryPlatformPostRepository()
        useCase = TransitionPlatformPostUseCase(platformPostRepository, postRepository)
    }

    @Test
    fun `valid transition from DRAFT to PENDING_REVIEW`() {
        val pp = createPlatformPost(PlatformPostStatus.DRAFT)
        val result = useCase.execute(pp.id, PlatformPostStatus.PENDING_REVIEW)

        assertEquals(PlatformPostStatus.PENDING_REVIEW, result.status)
    }

    @Test
    fun `invalid transition throws`() {
        val pp = createPlatformPost(PlatformPostStatus.PUBLISHED)

        assertThrows<IllegalArgumentException> {
            useCase.execute(pp.id, PlatformPostStatus.DRAFT)
        }
    }

    @Test
    fun `scheduledAt is set on SCHEDULED transition`() {
        val scheduledTime = Instant.now().plusSeconds(3600)
        val pp = createPlatformPost(PlatformPostStatus.DRAFT)
        val result = useCase.execute(pp.id, PlatformPostStatus.SCHEDULED, scheduledTime)

        assertEquals(PlatformPostStatus.SCHEDULED, result.status)
        assertEquals(scheduledTime, result.scheduledAt)
    }

    @Test
    fun `SCHEDULED transition without scheduledAt throws`() {
        val pp = createPlatformPost(PlatformPostStatus.DRAFT)

        assertThrows<IllegalArgumentException> {
            useCase.execute(pp.id, PlatformPostStatus.SCHEDULED)
        }
    }

    @Test
    fun `post scheduledAt is synced after transition`() {
        val post = postRepository.save(Post(
            id = UUID.randomUUID(),
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
        ))

        val scheduledTime = Instant.now().plusSeconds(3600)
        val pp = PlatformPost(
            id = UUID.randomUUID(),
            postId = post.id,
            socialAccountId = UUID.randomUUID(),
            platformTitle = null,
            platformCaption = null,
            platformFirstComment = null,
            platformMedia = null,
            platformExtra = null,
            status = PlatformPostStatus.DRAFT,
            platformPostId = "",
            publishError = "",
            publishedAt = null,
            scheduledAt = null,
            retryCount = 0,
            nextRetryAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        platformPostRepository.save(pp)

        useCase.execute(pp.id, PlatformPostStatus.SCHEDULED, scheduledTime)

        val updatedPost = postRepository.findById(post.id)!!
        assertEquals(scheduledTime, updatedPost.scheduledAt)
    }

    private fun createPlatformPost(status: PlatformPostStatus): PlatformPost {
        val post = postRepository.save(Post(
            id = UUID.randomUUID(),
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
        ))
        val pp = PlatformPost(
            id = UUID.randomUUID(),
            postId = post.id,
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
            scheduledAt = null,
            retryCount = 0,
            nextRetryAt = null,
            createdAt = Instant.now(),
            updatedAt = Instant.now(),
        )
        platformPostRepository.save(pp)
        return pp
    }
}

class TransitionInMemoryPostRepository : PostRepository {
    private val posts = mutableMapOf<UUID, Post>()
    override fun findById(id: UUID): Post? = posts[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Post> = posts.values.filter { it.workspaceId == workspaceId }
    override fun findByAuthorId(authorId: UUID): List<Post> = posts.values.filter { it.authorId == authorId }
    override fun save(post: Post): Post { posts[post.id] = post; return post }
    override fun update(post: Post): Post { posts[post.id] = post; return post }
    override fun delete(id: UUID) { posts.remove(id) }
}

class TransitionInMemoryPlatformPostRepository : PlatformPostRepository {
    private val platformPosts = mutableMapOf<UUID, PlatformPost>()
    override fun findById(id: UUID): PlatformPost? = platformPosts[id]
    override fun findByPostId(postId: UUID): List<PlatformPost> = platformPosts.values.filter { it.postId == postId }
    override fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost> = platformPosts.values.filter { it.socialAccountId == socialAccountId }
    override fun findByStatus(status: PlatformPostStatus): List<PlatformPost> = platformPosts.values.filter { it.status == status }
    override fun findScheduledBefore(time: Instant): List<PlatformPost> = platformPosts.values.filter { it.status == PlatformPostStatus.SCHEDULED && it.scheduledAt != null && it.scheduledAt!! <= time }
    override fun save(platformPost: PlatformPost): PlatformPost { platformPosts[platformPost.id] = platformPost; return platformPost }
    override fun update(platformPost: PlatformPost): PlatformPost { platformPosts[platformPost.id] = platformPost; return platformPost }
    override fun delete(id: UUID) { platformPosts.remove(id) }
}
