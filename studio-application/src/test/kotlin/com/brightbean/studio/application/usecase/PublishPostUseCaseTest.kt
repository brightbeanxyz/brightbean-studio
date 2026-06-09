package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.SocialProvider
import com.brightbean.studio.infrastructure.provider.types.PublishContent
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.util.UUID

class PublishPostUseCaseTest {

    private lateinit var postRepository: PostRepository
    private lateinit var socialAccountRepository: SocialAccountRepository
    private lateinit var platformPostRepository: PlatformPostRepository
    private lateinit var providerRegistry: ProviderRegistry
    private lateinit var publishPostUseCase: PublishPostUseCase

    private val workspaceId = UUID.randomUUID()
    private val authorId = UUID.randomUUID()
    private val facebookAccountId = UUID.randomUUID()
    private val instagramAccountId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        postRepository = InMemoryPostRepository()
        socialAccountRepository = InMemorySocialAccountRepository()
        platformPostRepository = InMemoryPlatformPostRepository()
        providerRegistry = ProviderRegistry.from(listOf(
            FakeFacebookProvider(),
            FakeInstagramProvider()
        ))
        publishPostUseCase = PublishPostUseCase(
            postRepository,
            socialAccountRepository,
            platformPostRepository,
            providerRegistry
        )

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
        socialAccountRepository.save(
            SocialAccount(
                id = instagramAccountId,
                workspaceId = workspaceId,
                credentialId = UUID.randomUUID(),
                platformType = PlatformType.INSTAGRAM,
                platformUserId = "ig_user_456",
                platformUsername = "testuser_insta",
                platformDisplayName = "Test User Instagram",
                isActive = true,
                connectedAt = Instant.now(),
            )
        )
    }

    @Test
    fun `publish post should publish to all platforms and return results`() {
        val post = postRepository.save(
            Post(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                authorId = authorId,
                title = "",
                caption = "Test content",
                firstComment = "",
                internalNotes = "",
                tags = emptyList(),
                categoryId = null,
                scheduledAt = null,
                publishedAt = null,
                createdAt = Instant.now(),
                updatedAt = Instant.now(),
            )
        )

        platformPostRepository.save(PlatformPost(
            id = UUID.randomUUID(), postId = post.id, socialAccountId = facebookAccountId,
            platformTitle = null, platformCaption = null, platformFirstComment = null,
            platformMedia = null, platformExtra = null, status = PlatformPostStatus.SCHEDULED,
            platformPostId = "", publishError = "", publishedAt = null,
            scheduledAt = Instant.now().minusSeconds(60),
            retryCount = 0, nextRetryAt = null, createdAt = Instant.now(), updatedAt = Instant.now(),
        ))
        platformPostRepository.save(PlatformPost(
            id = UUID.randomUUID(), postId = post.id, socialAccountId = instagramAccountId,
            platformTitle = null, platformCaption = null, platformFirstComment = null,
            platformMedia = null, platformExtra = null, status = PlatformPostStatus.SCHEDULED,
            platformPostId = "", publishError = "", publishedAt = null,
            scheduledAt = Instant.now().minusSeconds(60),
            retryCount = 0, nextRetryAt = null, createdAt = Instant.now(), updatedAt = Instant.now(),
        ))

        val results = publishPostUseCase.execute(post.id)

        assertEquals(2, results.size)
        assertTrue(results.all { it.success })

        val platformPosts = platformPostRepository.findByPostId(post.id)
        assertEquals(2, platformPosts.size)
        assertEquals(PlatformPostStatus.PUBLISHED, platformPosts[0].status)
        assertEquals(PlatformPostStatus.PUBLISHED, platformPosts[1].status)
    }

    @Test
    fun `publish post should throw when post not found`() {
        assertThrows<IllegalArgumentException> {
            publishPostUseCase.execute(UUID.randomUUID())
        }
    }

    @Test
    fun `publish post should throw when no schedulable platform posts found`() {
        val post = postRepository.save(
            Post(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                authorId = authorId,
                title = "",
                caption = "Test content",
                firstComment = "",
                internalNotes = "",
                tags = emptyList(),
                categoryId = null,
                scheduledAt = null,
                publishedAt = null,
                createdAt = Instant.now(),
                updatedAt = Instant.now(),
            )
        )

        assertThrows<IllegalArgumentException> {
            publishPostUseCase.execute(post.id)
        }
    }
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

    override fun publishPost(account: SocialAccount, content: PublishContent) = PublishResult(
        success = true,
        platformPostId = "fb_post_${account.id}",
        postUrl = "https://facebook.com/post/${account.id}",
        publishedAt = Instant.now(),
    )

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()
}

class FakeInstagramProvider : SocialProvider {
    override val platformType = PlatformType.INSTAGRAM

    override fun getProfile(socialAccount: SocialAccount) = PlatformProfile(
        platformUserId = socialAccount.platformUserId,
        platformUsername = socialAccount.platformUsername,
        platformDisplayName = socialAccount.platformDisplayName,
        profileUrl = socialAccount.profileUrl,
        platformAvatarUrl = socialAccount.platformAvatarUrl,
    )

    override fun publishPost(account: SocialAccount, content: PublishContent) = PublishResult(
        success = true,
        platformPostId = "ig_post_${account.id}",
        postUrl = "https://instagram.com/post/${account.id}",
        publishedAt = Instant.now(),
    )

    override fun getInboxItems(socialAccount: SocialAccount): List<com.brightbean.studio.domain.model.InboxItem> = emptyList()
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

    override fun findByStatus(status: PlatformPostStatus): List<PlatformPost> =
        platformPosts.values.filter { it.status == status }

    override fun findScheduledBefore(time: Instant): List<PlatformPost> =
        platformPosts.values.filter { it.status == PlatformPostStatus.SCHEDULED && it.scheduledAt != null && it.scheduledAt!!.compareTo(time) <= 0 }

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
