package com.brightbean.studio.application.usecase

import com.brightbean.studio.domain.model.Idea
import com.brightbean.studio.domain.model.IdeaMedia
import com.brightbean.studio.domain.model.IdeaStatus
import com.brightbean.studio.domain.model.PlatformPost
import com.brightbean.studio.domain.model.PlatformPostStatus
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Post
import com.brightbean.studio.domain.model.PostMedia
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.IdeaMediaRepository
import com.brightbean.studio.domain.repository.IdeaRepository
import com.brightbean.studio.domain.repository.PlatformPostRepository
import com.brightbean.studio.domain.repository.PostMediaRepository
import com.brightbean.studio.domain.repository.PostRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.Assertions.assertNull
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.assertThrows
import java.time.Instant
import java.util.UUID

class IdeaUseCasesTest {

    private lateinit var ideaRepository: IdeaRepository
    private lateinit var ideaMediaRepository: IdeaMediaRepository
    private lateinit var postRepository: IdeaInMemoryPostRepository
    private lateinit var platformPostRepository: IdeaInMemoryPlatformPostRepository
    private lateinit var postMediaRepository: IdeaInMemoryPostMediaRepository
    private lateinit var socialAccountRepository: SocialAccountRepository
    private lateinit var useCases: IdeaUseCases

    private val workspaceId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        ideaRepository = IdeaInMemoryRepository()
        ideaMediaRepository = IdeaInMemoryMediaRepository()
        postRepository = IdeaInMemoryPostRepository()
        platformPostRepository = IdeaInMemoryPlatformPostRepository()
        postMediaRepository = IdeaInMemoryPostMediaRepository()
        socialAccountRepository = IdeaInMemorySocialAccountRepository()
        useCases = IdeaUseCases(
            ideaRepository,
            ideaMediaRepository,
            postRepository,
            platformPostRepository,
            postMediaRepository,
            socialAccountRepository,
        )
    }

    @Test
    fun `create idea with media`() {
        val assetId = UUID.randomUUID()
        val idea = useCases.create(
            workspaceId = workspaceId,
            authorId = null,
            title = "My Idea",
            description = "A great idea",
            tags = listOf("tag1"),
            mediaAssetIds = listOf(assetId),
            groupId = null,
        )

        assertEquals("My Idea", idea.title)
        assertEquals(IdeaStatus.UNASSIGNED, idea.status)
        val media = ideaMediaRepository.findByIdeaId(idea.id)
        assertEquals(1, media.size)
        assertEquals(assetId, media[0].mediaAssetId)
    }

    @Test
    fun `update idea`() {
        val idea = useCases.create(workspaceId, null, "Old", "Desc", emptyList(), emptyList(), null)

        val updated = useCases.update(idea.id, "New", null, null, null, null)

        assertEquals("New", updated.title)
        assertEquals("Desc", updated.description)
    }

    @Test
    fun `delete idea cascades media`() {
        val assetId = UUID.randomUUID()
        val idea = useCases.create(workspaceId, null, "Delete Me", "", emptyList(), listOf(assetId), null)

        useCases.delete(idea.id)

        assertNull(ideaRepository.findById(idea.id))
        assertTrue(ideaMediaRepository.findByIdeaId(idea.id).isEmpty())
    }

    @Test
    fun `move idea to group`() {
        val idea = useCases.create(workspaceId, null, "Idea", "", emptyList(), emptyList(), null)
        val groupId = UUID.randomUUID()

        val moved = useCases.move(idea.id, groupId, 1)

        assertEquals(groupId, moved.groupId)
        assertEquals(1, moved.position)
        assertEquals(IdeaStatus.TODO, moved.status)
    }

    @Test
    fun `convert idea to post`() {
        val assetId = UUID.randomUUID()
        val idea = useCases.create(workspaceId, null, "Idea", "Desc", listOf("tag1"), listOf(assetId), null)

        val accountId = UUID.randomUUID()
        socialAccountRepository.save(SocialAccount(
            id = accountId,
            workspaceId = workspaceId,
            credentialId = UUID.randomUUID(),
            platformType = PlatformType.FACEBOOK,
            platformUserId = "fb_user",
            platformUsername = "testuser",
            platformDisplayName = "Test User",
            isActive = true,
            connectedAt = Instant.now(),
        ))

        val result = useCases.convertToPost(idea.id)

        assertNotNull(result.post)
        assertEquals("Idea", result.post.title)
        assertEquals("Desc", result.post.caption)
        assertEquals(1, result.platformPosts.size)
        assertEquals(PlatformPostStatus.DRAFT, result.platformPosts[0].status)

        val updatedIdea = ideaRepository.findById(idea.id)!!
        assertEquals(result.post.id, updatedIdea.postId)

        val postMedia = postMediaRepository.findByPostId(result.post.id)
        assertEquals(1, postMedia.size)
        assertEquals(assetId, postMedia[0].mediaAssetId)
    }

    @Test
    fun `convert already-converted idea throws`() {
        val idea = useCases.create(workspaceId, null, "Idea", "", emptyList(), emptyList(), null)

        socialAccountRepository.save(SocialAccount(
            id = UUID.randomUUID(),
            workspaceId = workspaceId,
            credentialId = UUID.randomUUID(),
            platformType = PlatformType.FACEBOOK,
            platformUserId = "fb_user",
            platformUsername = "testuser",
            platformDisplayName = "Test User",
            isActive = true,
            connectedAt = Instant.now(),
        ))
        useCases.convertToPost(idea.id)

        assertThrows<IllegalArgumentException> {
            useCases.convertToPost(idea.id)
        }
    }
}

class IdeaInMemoryRepository : IdeaRepository {
    private val ideas = mutableMapOf<UUID, Idea>()
    override fun findById(id: UUID): Idea? = ideas[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Idea> = ideas.values.filter { it.workspaceId == workspaceId }
    override fun findByGroupId(groupId: UUID): List<Idea> = ideas.values.filter { it.groupId == groupId }
    override fun findByAuthorId(authorId: UUID): List<Idea> = ideas.values.filter { it.authorId == authorId }
    override fun save(idea: Idea): Idea { ideas[idea.id] = idea; return idea }
    override fun update(idea: Idea): Idea { ideas[idea.id] = idea; return idea }
    override fun delete(id: UUID) { ideas.remove(id) }
}

class IdeaInMemoryMediaRepository : IdeaMediaRepository {
    private val media = mutableMapOf<UUID, IdeaMedia>()
    override fun findByIdeaId(ideaId: UUID): List<IdeaMedia> = media.values.filter { it.ideaId == ideaId }
    override fun save(m: IdeaMedia): IdeaMedia { media[m.id] = m; return m }
    override fun deleteByIdeaId(ideaId: UUID) { media.entries.removeIf { it.value.ideaId == ideaId } }
    override fun delete(id: UUID) { media.remove(id) }
}

class IdeaInMemoryPostRepository : PostRepository {
    private val posts = mutableMapOf<UUID, Post>()
    override fun findById(id: UUID): Post? = posts[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<Post> = posts.values.filter { it.workspaceId == workspaceId }
    override fun findByAuthorId(authorId: UUID): List<Post> = posts.values.filter { it.authorId == authorId }
    override fun save(post: Post): Post { posts[post.id] = post; return post }
    override fun update(post: Post): Post { posts[post.id] = post; return post }
    override fun delete(id: UUID) { posts.remove(id) }
}

class IdeaInMemoryPlatformPostRepository : PlatformPostRepository {
    private val platformPosts = mutableMapOf<UUID, PlatformPost>()
    override fun findById(id: UUID): PlatformPost? = platformPosts[id]
    override fun findByPostId(postId: UUID): List<PlatformPost> = platformPosts.values.filter { it.postId == postId }
    override fun findBySocialAccountId(socialAccountId: UUID): List<PlatformPost> = platformPosts.values.filter { it.socialAccountId == socialAccountId }
    override fun findByStatus(status: PlatformPostStatus): List<PlatformPost> = platformPosts.values.filter { it.status == status }
    override fun findScheduledBefore(time: Instant): List<PlatformPost> = emptyList()
    override fun save(platformPost: PlatformPost): PlatformPost { platformPosts[platformPost.id] = platformPost; return platformPost }
    override fun update(platformPost: PlatformPost): PlatformPost { platformPosts[platformPost.id] = platformPost; return platformPost }
    override fun delete(id: UUID) { platformPosts.remove(id) }
}

class IdeaInMemoryPostMediaRepository : PostMediaRepository {
    private val media = mutableMapOf<UUID, PostMedia>()
    override fun findByPostId(postId: UUID): List<PostMedia> = media.values.filter { it.postId == postId }
    override fun save(m: PostMedia): PostMedia { media[m.id] = m; return m }
    override fun delete(id: UUID) { media.remove(id) }
    override fun deleteByPostId(postId: UUID) { media.entries.removeIf { it.value.postId == postId } }
}

class IdeaInMemorySocialAccountRepository : SocialAccountRepository {
    private val accounts = mutableMapOf<UUID, SocialAccount>()
    override fun findById(id: UUID): SocialAccount? = accounts[id]
    override fun findByWorkspaceId(workspaceId: UUID): List<SocialAccount> = accounts.values.filter { it.workspaceId == workspaceId }
    override fun findByPlatformType(workspaceId: UUID, platformType: PlatformType): List<SocialAccount> = accounts.values.filter { it.workspaceId == workspaceId && it.platformType == platformType }
    override fun findActiveByWorkspace(workspaceId: UUID): List<SocialAccount> = accounts.values.filter { it.workspaceId == workspaceId && it.isActive }
    override fun save(socialAccount: SocialAccount): SocialAccount { accounts[socialAccount.id] = socialAccount; return socialAccount }
    override fun update(socialAccount: SocialAccount): SocialAccount { accounts[socialAccount.id] = socialAccount; return socialAccount }
    override fun delete(id: UUID) { accounts.remove(id) }
}
