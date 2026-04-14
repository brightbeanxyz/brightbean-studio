package com.brightbean.studio.application.worker

import com.brightbean.studio.domain.model.InboxItem
import com.brightbean.studio.domain.model.InboxItemType
import com.brightbean.studio.domain.model.PlatformType
import com.brightbean.studio.domain.model.Sentiment
import com.brightbean.studio.domain.model.SocialAccount
import com.brightbean.studio.domain.repository.InboxRepository
import com.brightbean.studio.domain.repository.SocialAccountRepository
import com.brightbean.studio.infrastructure.provider.ProviderRegistry
import com.brightbean.studio.infrastructure.provider.SocialProvider
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class InboxSyncWorkerTest {

    private lateinit var socialAccountRepository: SocialAccountRepository
    private lateinit var inboxRepository: InboxRepository
    private lateinit var providerRegistry: ProviderRegistry
    private lateinit var inboxSyncWorker: InboxSyncWorker

    private val workspaceId = UUID.randomUUID()
    private val facebookAccountId = UUID.randomUUID()
    private val instagramAccountId = UUID.randomUUID()

    @BeforeEach
    fun setUp() {
        socialAccountRepository = InMemorySocialAccountRepository()
        inboxRepository = InMemoryInboxRepository()
        providerRegistry = ProviderRegistry.from(listOf(InboxSyncWorkerFakeFacebookProvider(), InboxSyncWorkerFakeInstagramProvider()))
        inboxSyncWorker = InboxSyncWorker(socialAccountRepository, inboxRepository, providerRegistry)

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
                platformUsername = "testuser",
                platformDisplayName = "Test User",
                isActive = true,
                connectedAt = Instant.now(),
            )
        )
    }

    @Test
    fun `syncAllAccounts should sync all active accounts for workspace`() {
        inboxSyncWorker.syncAllAccounts(workspaceId)

        val fbAccount = socialAccountRepository.findById(facebookAccountId)
        val igAccount = socialAccountRepository.findById(instagramAccountId)

        assertTrue(fbAccount?.lastSyncAt != null, "fb account should have lastSyncAt set")
        assertTrue(igAccount?.lastSyncAt != null, "ig account should have lastSyncAt set")
    }

    @Test
    fun `syncAccount should fetch inbox items and save new ones`() {
        inboxSyncWorker.syncAccount(socialAccountRepository.findById(facebookAccountId)!!)

        val inboxItems = inboxRepository.findBySocialAccountId(facebookAccountId)
        assertTrue(inboxItems.size == 2)
    }

    @Test
    fun `syncAccount should update lastSyncAt on social account`() {
        val account = socialAccountRepository.findById(facebookAccountId)!!
        val beforeSync = account.lastSyncAt

        inboxSyncWorker.syncAccount(account)

        val afterSync = socialAccountRepository.findById(facebookAccountId)
        assert(afterSync?.lastSyncAt?.isAfter(beforeSync ?: Instant.MIN) == true)
    }

    @Test
    fun `syncAccount should not save duplicate items`() {
        val account = socialAccountRepository.findById(facebookAccountId)!!

        inboxSyncWorker.syncAccount(account)
        inboxSyncWorker.syncAccount(account)

        val inboxItems = inboxRepository.findBySocialAccountId(facebookAccountId)
        assertTrue(inboxItems.size == 2)
    }
}

class InMemoryInboxRepository : InboxRepository {
    private val items = mutableMapOf<UUID, InboxItem>()
    private val seenKeys = mutableSetOf<String>()

    override fun findById(id: UUID): InboxItem? = items[id]

    override fun findByWorkspaceId(workspaceId: UUID): List<InboxItem> =
        items.values.filter { it.workspaceId == workspaceId }

    override fun findBySocialAccountId(socialAccountId: UUID): List<InboxItem> =
        items.values.filter { it.socialAccountId == socialAccountId }

    override fun save(inboxItem: InboxItem): InboxItem {
        val key = "${inboxItem.socialAccountId}:${inboxItem.platformItemId}"
        if (seenKeys.contains(key)) {
            return inboxItem
        }
        seenKeys.add(key)
        items[inboxItem.id] = inboxItem
        return inboxItem
    }

    override fun update(inboxItem: InboxItem): InboxItem {
        items[inboxItem.id] = inboxItem
        return inboxItem
    }

    override fun delete(id: UUID) { items.remove(id) }
}

class InboxSyncWorkerFakeFacebookProvider : SocialProvider {
    override val platformType = PlatformType.FACEBOOK

    override fun authenticate(credential: com.brightbean.studio.domain.model.Credential) =
        com.brightbean.studio.infrastructure.provider.AuthResult(success = true)

    override fun refreshToken(credential: com.brightbean.studio.domain.model.Credential) =
        com.brightbean.studio.infrastructure.provider.AuthResult(success = true)

    override fun getProfile(socialAccount: SocialAccount) =
        com.brightbean.studio.infrastructure.provider.PlatformProfile(
            platformUserId = socialAccount.platformUserId,
            platformUsername = socialAccount.platformUsername,
            platformDisplayName = socialAccount.platformDisplayName,
            profileUrl = socialAccount.profileUrl,
            platformAvatarUrl = socialAccount.platformAvatarUrl,
        )

    override fun publish(post: com.brightbean.studio.domain.model.Post, socialAccount: SocialAccount) =
        com.brightbean.studio.infrastructure.provider.PublishResult(
            success = true,
            platformPostId = "fb_post_${post.id}",
            postUrl = "https://facebook.com/post/${post.id}",
            publishedAt = Instant.now(),
        )

    override fun getComments(postId: String): List<com.brightbean.studio.infrastructure.provider.Comment> = emptyList()

    override fun getInboxItems(socialAccount: SocialAccount): List<InboxItem> = listOf(
        InboxItem(
            id = UUID.randomUUID(),
            workspaceId = socialAccount.workspaceId,
            socialAccountId = socialAccount.id,
            platformType = PlatformType.FACEBOOK,
            platformItemId = "fb_inbox_1",
            type = InboxItemType.MESSAGE,
            content = "Hello from Facebook",
            authorName = "John Doe",
            authorAvatarUrl = null,
            mediaUrls = emptyList(),
            sentiment = Sentiment.POSITIVE,
            isRead = false,
            isArchived = false,
            platformCreatedAt = Instant.now(),
            receivedAt = Instant.now(),
        ),
        InboxItem(
            id = UUID.randomUUID(),
            workspaceId = socialAccount.workspaceId,
            socialAccountId = socialAccount.id,
            platformType = PlatformType.FACEBOOK,
            platformItemId = "fb_inbox_2",
            type = InboxItemType.COMMENT,
            content = "Great post!",
            authorName = "Jane Doe",
            authorAvatarUrl = null,
            mediaUrls = emptyList(),
            sentiment = Sentiment.POSITIVE,
            isRead = false,
            isArchived = false,
            platformCreatedAt = Instant.now(),
            receivedAt = Instant.now(),
        ),
    )

    override fun getInsights(postId: String): com.brightbean.studio.infrastructure.provider.PostInsights? = null
}

class InboxSyncWorkerFakeInstagramProvider : SocialProvider {
    override val platformType = PlatformType.INSTAGRAM

    override fun authenticate(credential: com.brightbean.studio.domain.model.Credential) =
        com.brightbean.studio.infrastructure.provider.AuthResult(success = true)

    override fun refreshToken(credential: com.brightbean.studio.domain.model.Credential) =
        com.brightbean.studio.infrastructure.provider.AuthResult(success = true)

    override fun getProfile(socialAccount: SocialAccount) =
        com.brightbean.studio.infrastructure.provider.PlatformProfile(
            platformUserId = socialAccount.platformUserId,
            platformUsername = socialAccount.platformUsername,
            platformDisplayName = socialAccount.platformDisplayName,
            profileUrl = socialAccount.profileUrl,
            platformAvatarUrl = socialAccount.platformAvatarUrl,
        )

    override fun publish(post: com.brightbean.studio.domain.model.Post, socialAccount: SocialAccount) =
        com.brightbean.studio.infrastructure.provider.PublishResult(
            success = true,
            platformPostId = "ig_post_${post.id}",
            postUrl = "https://instagram.com/post/${post.id}",
            publishedAt = Instant.now(),
        )

    override fun getComments(postId: String): List<com.brightbean.studio.infrastructure.provider.Comment> = emptyList()

    override fun getInboxItems(socialAccount: SocialAccount): List<InboxItem> = listOf(
        InboxItem(
            id = UUID.randomUUID(),
            workspaceId = socialAccount.workspaceId,
            socialAccountId = socialAccount.id,
            platformType = PlatformType.INSTAGRAM,
            platformItemId = "ig_inbox_1",
            type = InboxItemType.MENTION,
            content = "Tagged you in a post",
            authorName = "Tag User",
            authorAvatarUrl = null,
            mediaUrls = emptyList(),
            sentiment = Sentiment.NEUTRAL,
            isRead = false,
            isArchived = false,
            platformCreatedAt = Instant.now(),
            receivedAt = Instant.now(),
        ),
    )

    override fun getInsights(postId: String): com.brightbean.studio.infrastructure.provider.PostInsights? = null
}