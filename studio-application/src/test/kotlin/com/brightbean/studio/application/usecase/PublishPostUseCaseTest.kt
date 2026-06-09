package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostStatus
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.PlatformProfile
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.PublishResult
import com.brightbean.studio.infrastructure.provider.SocialProvider
import org.junit.jupiter.api.Assertions.assertEquals
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
    fun `publish post should publish to all platforms and update post status`() {
        val post = postRepository.save(
            Post(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                authorId = authorId,
                content = "Test content",
                platforms = listOf(PlatformType.FACEBOOK, PlatformType.INSTAGRAM),
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

        val result = publishPostUseCase.execute(post.id)

        assertEquals(PostStatus.PUBLISHED, result.status)
        assertEquals(post.id, result.id)

        val platformPosts = platformPostRepository.findByPostId(post.id)
        assertEquals(2, platformPosts.size)
    }

    @Test
    fun `publish post should throw when post not found`() {
        assertThrows<IllegalArgumentException> {
            publishPostUseCase.execute(UUID.randomUUID())
        }
    }

    @Test
    fun `publish post should throw when post requires approval`() {
        val post = postRepository.save(
            Post(
                id = UUID.randomUUID(),
                workspaceId = workspaceId,
                authorId = authorId,
                content = "Test content requiring approval",
                platforms = listOf(PlatformType.FACEBOOK),
                categoryId = null,
                tags = emptyList(),
                status = PostStatus.PENDING_APPROVAL,
                scheduledAt = null,
                publishedAt = null,
                mediaIds = emptyList(),
                createdAt = Instant.now(),
                updatedAt = Instant.now(),
            )
        )

        assertThrows<IllegalArgumentException> {
            publishPostUseCase.execute(post.id)
        }
    }

    @Test
    fun `publish post should throw when no social accounts found`() {
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

    override fun publishPost(account: SocialAccount, content: com.brightbean.studio.infrastructure.provider.types.PublishContent) = PublishResult(
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

    override fun publishPost(account: SocialAccount, content: com.brightbean.studio.infrastructure.provider.types.PublishContent) = PublishResult(
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
