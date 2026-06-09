package com.brightbean.studio.application.worker

import com.brightbean.studio.application.usecase.PublishPostUseCase
import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.QueueStatus
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.PublishingQueueRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.SocialProvider
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class PublishingWorkerTest {

    private lateinit var postRepository: PostRepository
    private lateinit var socialAccountRepository: SocialAccountRepository
    private lateinit var platformPostRepository: PlatformPostRepository
    private lateinit var publishingQueueRepository: PublishingQueueRepository
    private lateinit var providerRegistry: ProviderRegistry
    private lateinit var publishPostUseCase: PublishPostUseCase
    private lateinit var publishingWorker: PublishingWorker

    private val workspaceId = UUID.randomUUID()
    private val authorId = UUID.randomUUID()
    private val facebookAccountId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        postRepository = InMemoryPostRepository()
        socialAccountRepository = InMemorySocialAccountRepository()
        platformPostRepository = InMemoryPlatformPostRepository()
        publishingQueueRepository = InMemoryPublishingQueueRepository()
        providerRegistry = ProviderRegistry.from(listOf(FakeFacebookProvider()))
        publishPostUseCase = PublishPostUseCase(
            postRepository,
            socialAccountRepository,
            platformPostRepository,
            providerRegistry
        )
        publishingWorker = PublishingWorker(publishingQueueRepository, publishPostUseCase)

        socialAccountRepository.save(
            SocialAccount(
                id = facebookAccountId,
                workspaceId = workspaceId,
                credentialId = UUID.randomUUID(),
                platformType = PlatformType.FACEBOOK,
                platformUserId = "fb_user_123",
                platformUsername = "testuser",
                platformDisplayName = "Test User",
                isActive = true,
                connectedAt = Instant.now(),
            )
        )
    }

    @Test
    fun `processQueue should process pending items and mark as completed`() {
        val post = postRepository.save(
            Post(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                authorId = authorId,
                content = "Test content",
                platforms = listOf(PlatformType.FACEBOOK),
                categoryId = null,
                tags = emptyList(),
                status = PostStatus.DRAFT,
                scheduledAt = null,
                publishedAt = null,
                mediaIds = emptyList(),
                createdAt = Instant.now(),
                updatedAt = Instant.now(),
            )
        )

        val queueItem = publishingQueueRepository.save(
            com.brightbean.studio.domain.model.PublishingQueue(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                postId = post.id,
                scheduledFor = Instant.now().minusSeconds(60),
                attempts = 0,
                lastAttemptAt = null,
                status = QueueStatus.PENDING,
                errorMessage = null,
            )
        )

        publishingWorker.processQueue()

        val updatedQueue = publishingQueueRepository.findById(queueItem.id)
        assertEquals(QueueStatus.COMPLETED, updatedQueue?.status)
    }

    @Test
    fun `processItem should increment attempts on failure`() {
        val post = postRepository.save(
            Post(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                authorId = authorId,
                content = "Test content",
                platforms = listOf(PlatformType.TIKTOK),
                categoryId = null,
                tags = emptyList(),
                status = PostStatus.DRAFT,
                scheduledAt = null,
                publishedAt = null,
                mediaIds = emptyList(),
                createdAt = Instant.now(),
                updatedAt = Instant.now(),
            )
        )

        val queueItem = publishingQueueRepository.save(
            com.brightbean.studio.domain.model.PublishingQueue(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                postId = post.id,
                scheduledFor = Instant.now().minusSeconds(60),
                attempts = 0,
                lastAttemptAt = null,
                status = QueueStatus.PENDING,
                errorMessage = null,
            )
        )

        publishingWorker.processItem(queueItem.id)

        val updatedQueue = publishingQueueRepository.findById(queueItem.id)
        assertEquals(1, updatedQueue?.attempts)
    }
}

class InMemoryPublishingQueueRepository : PublishingQueueRepository {
    private val queues = mutableMapOf<UUID, com.brightbean.studio.domain.model.PublishingQueue>()

    override fun findById(id: UUID): com.brightbean.studio.domain.model.PublishingQueue? = queues[id]

    override fun findByPostId(postId: UUID): List<com.brightbean.studio.domain.model.PublishingQueue> =
        queues.values.filter { it.postId == postId }

    override fun findByWorkspaceId(workspaceId: UUID): List<com.brightbean.studio.domain.model.PublishingQueue> =
        queues.values.filter { it.workspaceId == workspaceId }

    override fun findPending(): List<com.brightbean.studio.domain.model.PublishingQueue> =
        queues.values.filter { it.status == QueueStatus.PENDING }

    override fun save(queue: com.brightbean.studio.domain.model.PublishingQueue): com.brightbean.studio.domain.model.PublishingQueue {
        queues[queue.id] = queue
        return queue
    }

    override fun update(queue: com.brightbean.studio.domain.model.PublishingQueue): com.brightbean.studio.domain.model.PublishingQueue {
        queues[queue.id] = queue
        return queue
    }

    override fun delete(id: UUID) { queues.remove(id) }
}

class InMemoryPostRepository : PostRepository {
    private val posts = mutableMapOf<UUID, Post>()

    override fun findById(id: UUID): Post? = posts[id]

    override fun findByWorkspaceId(workspaceId: UUID): List<Post> =
        posts.values.filter { it.workspaceId == workspaceId }

    override fun findByAuthorId(authorId: UUID): List<Post> =
        posts.values.filter { it.authorId == authorId }

    override fun save(post: Post): Post {
        posts[post.id] = post
        return post
    }

    override fun update(post: Post): Post {
        posts[post.id] = post
        return post
    }

    override fun delete(id: UUID) { posts.remove(id) }
}

class InMemorySocialAccountRepository : SocialAccountRepository {
    private val accounts = mutableMapOf<UUID, SocialAccount>()

    override fun findById(id: UUID): SocialAccount? = accounts[id]

    override fun findByWorkspaceId(workspaceId: UUID): List<SocialAccount> =
        accounts.values.filter { it.workspaceId == workspaceId }

    override fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): List<SocialAccount> =
        accounts.values.filter { it.workspaceId == workspaceId && it.platformType == platformType }

    override fun findActiveByWorkspace(workspaceId: UUID): List<SocialAccount> =
        accounts.values.filter { it.workspaceId == workspaceId && it.isActive }

    override fun save(socialAccount: SocialAccount): SocialAccount {
        accounts[socialAccount.id] = socialAccount
        return socialAccount
    }

    override fun update(socialAccount: SocialAccount): SocialAccount {
        accounts[socialAccount.id] = socialAccount
        return socialAccount
    }

    override fun delete(id: UUID) { accounts.remove(id) }
}

class InMemoryPlatformPostRepository : PlatformPostRepository {
    private val platformPosts = mutableMapOf<UUID, PlatformPost>()

    override fun findById(id: UUID): PlatformPost? = platformPosts[id]

    override fun findByPostId(postId: UUID): List<PlatformPost> =
        platformPosts.values.filter { it.postId == postId }

    override fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost> =
        platformPosts.values.filter { it.socialAccountId == socialAccountId }

    override fun save(platformPost: PlatformPost): PlatformPost {
        platformPosts[platformPost.id] = platformPost
        return platformPost
    }

    override fun update(platformPost: PlatformPost): PlatformPost {
        platformPosts[platformPost.id] = platformPost
        return platformPost
    }

    override fun delete(id: UUID) { platformPosts.remove(id) }
}

class FakeFacebookProvider : SocialProvider {
    override val platformType = PlatformType.FACEBOOK

    override fun getProfile(socialAccount: SocialAccount) = PlatformProfile(
        platformUserId = socialAccount.platformUserId,
        platformUsername = socialAccount.platformUsername,
        platformDisplayName = socialAccount.platformDisplayName,
        profileUrl = socialAccount.profileUrl,
        platformAvatarUrl = socialAccount.platformAvatarUrl,
    )

    override fun publishPost(account: SocialAccount, content: com.brightbean.studio.infrastructure.provider.types.PublishContent) = PublishResult(
        success = true,
        platformPostId = "fb_post_${account.id}",
        postUrl = "https://facebook.com/post/${account.id}",
        publishedAt = Instant.now(),
    )

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()
}