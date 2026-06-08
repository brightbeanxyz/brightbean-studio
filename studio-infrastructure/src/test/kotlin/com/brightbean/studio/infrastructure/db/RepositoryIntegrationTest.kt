package com.brightbean.studio.infrastructure.db

import com.brightbean.studio.domain.model.*
import org.jdbi.v3.core.Jdbi
import org.jdbi.v3.core.kotlin.KotlinPlugin
import org.jdbi.v3.sqlobject.kotlin.KotlinSqlObjectPlugin
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.util.UUID

class RepositoryIntegrationTest {

    private lateinit var jdbi: Jdbi
    private lateinit var memberRepo: JDBIMemberRepository
    private lateinit var credentialRepo: JDBICredentialRepository
    private lateinit var socialAccountRepo: JDBISocialAccountRepository
    private lateinit var postRepo: JDBIPostRepository
    private lateinit var publishingQueueRepo: JDBIPublishingQueueRepository
    private lateinit var platformPostRepo: JDBIPlatformPostRepository
    private lateinit var inboxRepo: JDBIInboxRepository
    private lateinit var approvalRequestRepo: JDBIApprovalRequestRepository
    private lateinit var organizationRepo: JDBIOrganizationRepository
    private lateinit var orgMembershipRepo: JDBIOrgMembershipRepository
    private lateinit var workspaceMembershipRepo: JDBIWorkspaceMembershipRepository
    private lateinit var customRoleRepo: JDBICustomRoleRepository
    private lateinit var invitationRepo: JDBIInvitationRepository

    @BeforeEach
    fun setUp() {
        jdbi = Jdbi.create("jdbc:h2:mem:test_${UUID.randomUUID()};DB_CLOSE_DELAY=-1")
        jdbi.installPlugin(KotlinPlugin())
        jdbi.installPlugin(KotlinSqlObjectPlugin())

        jdbi.useHandle<Exception> { handle ->
            handle.createUpdate("""
                CREATE TABLE member (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    user_id UUID NOT NULL,
                    role VARCHAR NOT NULL,
                    invited_by UUID,
                    joined_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE credential (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    platform_type VARCHAR NOT NULL,
                    encrypted_access_token VARCHAR NOT NULL,
                    encrypted_refresh_token VARCHAR,
                    token_expires_at TIMESTAMP,
                    metadata VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE social_account (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    credential_id UUID NOT NULL,
                    platform_type VARCHAR NOT NULL,
                    platform_user_id VARCHAR NOT NULL,
                    platform_username VARCHAR NOT NULL,
                    platform_display_name VARCHAR NOT NULL,
                    platform_avatar_url VARCHAR,
                    profile_url VARCHAR,
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    metadata VARCHAR NOT NULL,
                    connected_at TIMESTAMP NOT NULL,
                    last_sync_at TIMESTAMP
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE post (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    author_id UUID NOT NULL,
                    content VARCHAR NOT NULL,
                    platforms VARCHAR NOT NULL,
                    category_id UUID,
                    tags VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    scheduled_at TIMESTAMP,
                    published_at TIMESTAMP,
                    media_ids VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE publishing_queue (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    post_id UUID NOT NULL,
                    scheduled_for TIMESTAMP NOT NULL,
                    attempts INT NOT NULL DEFAULT 0,
                    last_attempt_at TIMESTAMP,
                    status VARCHAR NOT NULL DEFAULT 'PENDING',
                    error_message VARCHAR
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE platform_post (
                    id UUID PRIMARY KEY,
                    post_id UUID NOT NULL,
                    social_account_id UUID NOT NULL,
                    platform_post_id VARCHAR,
                    platform_url VARCHAR,
                    status VARCHAR NOT NULL DEFAULT 'DRAFT',
                    error_message VARCHAR,
                    published_at TIMESTAMP
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE inbox_item (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    social_account_id UUID NOT NULL,
                    platform_type VARCHAR NOT NULL,
                    platform_item_id VARCHAR NOT NULL,
                    type VARCHAR NOT NULL,
                    content VARCHAR NOT NULL,
                    author_name VARCHAR NOT NULL,
                    author_avatar_url VARCHAR,
                    media_urls VARCHAR,
                    sentiment VARCHAR,
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
                    platform_created_at TIMESTAMP NOT NULL,
                    received_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE approval_request (
                    id UUID PRIMARY KEY,
                    workspace_id UUID NOT NULL,
                    post_id UUID NOT NULL,
                    requested_by UUID NOT NULL,
                    requested_at TIMESTAMP NOT NULL,
                    status VARCHAR NOT NULL DEFAULT 'PENDING',
                    reviewed_by UUID,
                    reviewed_at TIMESTAMP,
                    comment VARCHAR
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE organization (
                    id UUID PRIMARY KEY,
                    name VARCHAR NOT NULL,
                    logo_url VARCHAR,
                    default_timezone VARCHAR NOT NULL DEFAULT 'UTC',
                    billing_email VARCHAR NOT NULL DEFAULT '',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE org_membership (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    organization_id UUID NOT NULL,
                    org_role VARCHAR NOT NULL DEFAULT 'MEMBER',
                    invited_at TIMESTAMP NOT NULL,
                    accepted_at TIMESTAMP
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE workspace_membership (
                    id UUID PRIMARY KEY,
                    user_id UUID NOT NULL,
                    workspace_id UUID NOT NULL,
                    workspace_role VARCHAR NOT NULL DEFAULT 'VIEWER',
                    custom_role_id UUID,
                    added_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE custom_role (
                    id UUID PRIMARY KEY,
                    organization_id UUID NOT NULL,
                    name VARCHAR NOT NULL,
                    permissions TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            """).execute()

            handle.createUpdate("""
                CREATE TABLE invitation (
                    id UUID PRIMARY KEY,
                    organization_id UUID NOT NULL,
                    email VARCHAR NOT NULL,
                    org_role VARCHAR NOT NULL DEFAULT 'MEMBER',
                    workspace_assignments TEXT NOT NULL,
                    invited_by UUID,
                    token VARCHAR NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    accepted_at TIMESTAMP,
                    status VARCHAR NOT NULL DEFAULT 'PENDING',
                    created_at TIMESTAMP NOT NULL
                )
            """).execute()
        }

        memberRepo = JDBIMemberRepository(jdbi)
        credentialRepo = JDBICredentialRepository(jdbi)
        socialAccountRepo = JDBISocialAccountRepository(jdbi)
        postRepo = JDBIPostRepository(jdbi)
        publishingQueueRepo = JDBIPublishingQueueRepository(jdbi)
        platformPostRepo = JDBIPlatformPostRepository(jdbi)
        inboxRepo = JDBIInboxRepository(jdbi)
        approvalRequestRepo = JDBIApprovalRequestRepository(jdbi)
        organizationRepo = JDBIOrganizationRepository(jdbi)
        orgMembershipRepo = JDBIOrgMembershipRepository(jdbi)
        workspaceMembershipRepo = JDBIWorkspaceMembershipRepository(jdbi)
        customRoleRepo = JDBICustomRoleRepository(jdbi)
        invitationRepo = JDBIInvitationRepository(jdbi)
    }

    @Test
    fun `member save and findById`() {
        val member = createTestMember()
        memberRepo.save(member)

        val found = memberRepo.findById(member.id)

        assertNotNull(found)
        assertEquals(member.id, found!!.id)
        assertEquals(member.workspaceId, found.workspaceId)
        assertEquals(member.userId, found.userId)
        assertEquals(MemberRole.EDITOR, found.role)
    }

    @Test
    fun `member findByWorkspaceId returns members`() {
        val wsId = UUID.randomUUID()
        val m1 = createTestMember(workspaceId = wsId)
        val m2 = createTestMember(workspaceId = wsId)
        memberRepo.save(m1)
        memberRepo.save(m2)

        val results = memberRepo.findByWorkspaceId(wsId)

        assertEquals(2, results.size)
    }

    @Test
    fun `member delete removes member`() {
        val member = createTestMember()
        memberRepo.save(member)

        memberRepo.delete(member.id)

        assertNull(memberRepo.findById(member.id))
    }

    @Test
    fun `credential save and findById`() {
        val credential = createTestCredential()
        credentialRepo.save(credential)

        val found = credentialRepo.findById(credential.id)

        assertNotNull(found)
        assertEquals(credential.id, found!!.id)
        assertEquals(PlatformType.INSTAGRAM, found.platformType)
        assertEquals("encrypted-token", found.encryptedAccessToken)
    }

    @Test
    fun `credential findByPlatformType returns credential`() {
        val wsId = UUID.randomUUID()
        val credential = createTestCredential(workspaceId = wsId)
        credentialRepo.save(credential)

        val found = credentialRepo.findByPlatformType(wsId, PlatformType.INSTAGRAM)

        assertNotNull(found)
        assertEquals(credential.id, found!!.id)
    }

    @Test
    fun `credential delete removes credential`() {
        val credential = createTestCredential()
        credentialRepo.save(credential)

        credentialRepo.delete(credential.id)

        assertNull(credentialRepo.findById(credential.id))
    }

    @Test
    fun `socialAccount save and findById`() {
        val account = createTestSocialAccount()
        socialAccountRepo.save(account)

        val found = socialAccountRepo.findById(account.id)

        assertNotNull(found)
        assertEquals(account.id, found!!.id)
        assertEquals("ig_user_123", found.platformUserId)
        assertTrue(found.isActive)
    }

    @Test
    fun `socialAccount findActiveByWorkspace returns active accounts`() {
        val wsId = UUID.randomUUID()
        val active = createTestSocialAccount(workspaceId = wsId, isActive = true)
        val inactive = createTestSocialAccount(workspaceId = wsId, isActive = false)
        socialAccountRepo.save(active)
        socialAccountRepo.save(inactive)

        val results = socialAccountRepo.findActiveByWorkspace(wsId)

        assertEquals(1, results.size)
        assertEquals(active.id, results[0].id)
    }

    @Test
    fun `socialAccount delete removes account`() {
        val account = createTestSocialAccount()
        socialAccountRepo.save(account)

        socialAccountRepo.delete(account.id)

        assertNull(socialAccountRepo.findById(account.id))
    }

    @Test
    fun `post save and findById`() {
        val post = createTestPost()
        postRepo.save(post)

        val found = postRepo.findById(post.id)

        assertNotNull(found)
        assertEquals(post.id, found!!.id)
        assertEquals("Hello world", found.content)
        assertEquals(PostStatus.DRAFT, found.status)
        assertEquals(listOf(PlatformType.INSTAGRAM), found.platforms)
    }

    @Test
    fun `post findByAuthorId returns posts`() {
        val authorId = UUID.randomUUID()
        val p1 = createTestPost(authorId = authorId)
        val p2 = createTestPost(authorId = authorId)
        postRepo.save(p1)
        postRepo.save(p2)

        val results = postRepo.findByAuthorId(authorId)

        assertEquals(2, results.size)
    }

    @Test
    fun `post delete removes post`() {
        val post = createTestPost()
        postRepo.save(post)

        postRepo.delete(post.id)

        assertNull(postRepo.findById(post.id))
    }

    @Test
    fun `publishingQueue save and findById`() {
        val queue = createTestPublishingQueue()
        publishingQueueRepo.save(queue)

        val found = publishingQueueRepo.findById(queue.id)

        assertNotNull(found)
        assertEquals(queue.id, found!!.id)
        assertEquals(QueueStatus.PENDING, found.status)
        assertEquals(0, found.attempts)
    }

    @Test
    fun `publishingQueue findPending returns pending items`() {
        val pending = createTestPublishingQueue(status = QueueStatus.PENDING)
        val completed = createTestPublishingQueue(status = QueueStatus.COMPLETED)
        publishingQueueRepo.save(pending)
        publishingQueueRepo.save(completed)

        val results = publishingQueueRepo.findPending()

        assertTrue(results.any { it.id == pending.id })
        assertTrue(results.none { it.id == completed.id })
    }

    @Test
    fun `publishingQueue delete removes item`() {
        val queue = createTestPublishingQueue()
        publishingQueueRepo.save(queue)

        publishingQueueRepo.delete(queue.id)

        assertNull(publishingQueueRepo.findById(queue.id))
    }

    @Test
    fun `platformPost save and findById`() {
        val pp = createTestPlatformPost()
        platformPostRepo.save(pp)

        val found = platformPostRepo.findById(pp.id)

        assertNotNull(found)
        assertEquals(pp.id, found!!.id)
        assertEquals("ig_post_789", found.platformPostId)
        assertEquals(PostStatus.DRAFT, found.status)
    }

    @Test
    fun `platformPost findByPostId returns platform posts`() {
        val postId = UUID.randomUUID()
        val pp1 = createTestPlatformPost(postId = postId)
        val pp2 = createTestPlatformPost(postId = postId)
        platformPostRepo.save(pp1)
        platformPostRepo.save(pp2)

        val results = platformPostRepo.findByPostId(postId)

        assertEquals(2, results.size)
    }

    @Test
    fun `platformPost delete removes item`() {
        val pp = createTestPlatformPost()
        platformPostRepo.save(pp)

        platformPostRepo.delete(pp.id)

        assertNull(platformPostRepo.findById(pp.id))
    }

    @Test
    fun `inboxItem save and findById`() {
        val item = createTestInboxItem()
        inboxRepo.save(item)

        val found = inboxRepo.findById(item.id)

        assertNotNull(found)
        assertEquals(item.id, found!!.id)
        assertEquals(InboxItemType.COMMENT, found.type)
        assertEquals(Sentiment.POSITIVE, found.sentiment)
        assertFalse(found.isRead)
    }

    @Test
    fun `inboxItem findByWorkspaceId returns items`() {
        val wsId = UUID.randomUUID()
        val i1 = createTestInboxItem(workspaceId = wsId)
        val i2 = createTestInboxItem(workspaceId = wsId)
        inboxRepo.save(i1)
        inboxRepo.save(i2)

        val results = inboxRepo.findByWorkspaceId(wsId)

        assertEquals(2, results.size)
    }

    @Test
    fun `inboxItem delete removes item`() {
        val item = createTestInboxItem()
        inboxRepo.save(item)

        inboxRepo.delete(item.id)

        assertNull(inboxRepo.findById(item.id))
    }

    @Test
    fun `approvalRequest save and findById`() {
        val request = createTestApprovalRequest()
        approvalRequestRepo.save(request)

        val found = approvalRequestRepo.findById(request.id)

        assertNotNull(found)
        assertEquals(request.id, found!!.id)
        assertEquals(ApprovalStatus.PENDING, found.status)
    }

    @Test
    fun `approvalRequest findByPostId returns requests`() {
        val postId = UUID.randomUUID()
        val r1 = createTestApprovalRequest(postId = postId)
        val r2 = createTestApprovalRequest(postId = postId)
        approvalRequestRepo.save(r1)
        approvalRequestRepo.save(r2)

        val results = approvalRequestRepo.findByPostId(postId)

        assertEquals(2, results.size)
    }

    @Test
    fun `approvalRequest delete removes request`() {
        val request = createTestApprovalRequest()
        approvalRequestRepo.save(request)

        approvalRequestRepo.delete(request.id)

        assertNull(approvalRequestRepo.findById(request.id))
    }

    private fun createTestMember(
        workspaceId: UUID = UUID.randomUUID(),
    ) = Member(
        id = UUID.randomUUID(),
        workspaceId = workspaceId,
        userId = UUID.randomUUID(),
        role = MemberRole.EDITOR,
        invitedBy = UUID.randomUUID(),
        joinedAt = Instant.now(),
    )

    private fun createTestCredential(
        workspaceId: UUID = UUID.randomUUID(),
    ) = Credential(
        id = UUID.randomUUID(),
        workspaceId = workspaceId,
        platformType = PlatformType.INSTAGRAM,
        encryptedAccessToken = "encrypted-token",
        encryptedRefreshToken = "encrypted-refresh",
        tokenExpiresAt = Instant.now().plusSeconds(3600),
        metadata = mapOf("scope" to "read write"),
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    )

    private fun createTestSocialAccount(
        workspaceId: UUID = UUID.randomUUID(),
        isActive: Boolean = true,
    ) = SocialAccount(
        id = UUID.randomUUID(),
        workspaceId = workspaceId,
        credentialId = UUID.randomUUID(),
        platformType = PlatformType.INSTAGRAM,
        platformUserId = "ig_user_123",
        platformUsername = "testuser",
        platformDisplayName = "Test User",
        platformAvatarUrl = "https://example.com/avatar.jpg",
        profileUrl = "https://instagram.com/testuser",
        isActive = isActive,
        metadata = mapOf("followers" to "1000"),
        connectedAt = Instant.now(),
        lastSyncAt = null,
    )

    private fun createTestPost(
        authorId: UUID = UUID.randomUUID(),
    ) = Post(
        id = UUID.randomUUID(),
        workspaceId = UUID.randomUUID(),
        authorId = authorId,
        content = "Hello world",
        platforms = listOf(PlatformType.INSTAGRAM),
        categoryId = null,
        tags = emptyList(),
        status = PostStatus.DRAFT,
        scheduledAt = null,
        publishedAt = null,
        mediaIds = emptyList(),
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    )

    private fun createTestPublishingQueue(
        status: QueueStatus = QueueStatus.PENDING,
    ) = PublishingQueue(
        id = UUID.randomUUID(),
        workspaceId = UUID.randomUUID(),
        postId = UUID.randomUUID(),
        scheduledFor = Instant.now().plusSeconds(3600),
        attempts = 0,
        lastAttemptAt = null,
        status = status,
        errorMessage = null,
    )

    private fun createTestPlatformPost(
        postId: UUID = UUID.randomUUID(),
    ) = PlatformPost(
        id = UUID.randomUUID(),
        postId = postId,
        socialAccountId = UUID.randomUUID(),
        platformPostId = "ig_post_789",
        platformUrl = "https://instagram.com/p/789",
        status = PostStatus.DRAFT,
        errorMessage = null,
        publishedAt = null,
    )

    private fun createTestInboxItem(
        workspaceId: UUID = UUID.randomUUID(),
    ) = InboxItem(
        id = UUID.randomUUID(),
        workspaceId = workspaceId,
        socialAccountId = UUID.randomUUID(),
        platformType = PlatformType.INSTAGRAM,
        platformItemId = "ig_comment_456",
        type = InboxItemType.COMMENT,
        content = "Great post!",
        authorName = "Jane Doe",
        authorAvatarUrl = "https://example.com/jane.jpg",
        mediaUrls = emptyList(),
        sentiment = Sentiment.POSITIVE,
        isRead = false,
        isArchived = false,
        platformCreatedAt = Instant.now(),
        receivedAt = Instant.now(),
    )

    private fun createTestApprovalRequest(
        postId: UUID = UUID.randomUUID(),
    ) = ApprovalRequest(
        id = UUID.randomUUID(),
        workspaceId = UUID.randomUUID(),
        postId = postId,
        requestedBy = UUID.randomUUID(),
        requestedAt = Instant.now(),
        status = ApprovalStatus.PENDING,
        reviewedBy = null,
        reviewedAt = null,
        comment = null,
    )

    @Test
    fun `organization save and findById`() {
        val org = createTestOrganization()
        organizationRepo.save(org)

        val found = organizationRepo.findById(org.id)

        assertNotNull(found)
        assertEquals(org.id, found!!.id)
        assertEquals("Test Org", found.name)
        assertEquals("UTC", found.defaultTimezone)
    }

    @Test
    fun `organization delete removes organization`() {
        val org = createTestOrganization()
        organizationRepo.save(org)

        organizationRepo.delete(org.id)

        assertNull(organizationRepo.findById(org.id))
    }

    @Test
    fun `orgMembership save and findById`() {
        val membership = createTestOrgMembership()
        orgMembershipRepo.save(membership)

        val found = orgMembershipRepo.findById(membership.id)

        assertNotNull(found)
        assertEquals(membership.id, found!!.id)
        assertEquals(OrgRole.MEMBER, found.orgRole)
    }

    @Test
    fun `orgMembership findByOrganizationId returns memberships`() {
        val orgId = UUID.randomUUID()
        val m1 = createTestOrgMembership(organizationId = orgId)
        val m2 = createTestOrgMembership(organizationId = orgId)
        orgMembershipRepo.save(m1)
        orgMembershipRepo.save(m2)

        val results = orgMembershipRepo.findByOrganizationId(orgId)

        assertEquals(2, results.size)
    }

    @Test
    fun `workspaceMembership save and findById`() {
        val membership = createTestWorkspaceMembership()
        workspaceMembershipRepo.save(membership)

        val found = workspaceMembershipRepo.findById(membership.id)

        assertNotNull(found)
        assertEquals(membership.id, found!!.id)
        assertEquals(WorkspaceRole.EDITOR, found.workspaceRole)
    }

    @Test
    fun `workspaceMembership findByWorkspaceId returns memberships`() {
        val wsId = UUID.randomUUID()
        val m1 = createTestWorkspaceMembership(workspaceId = wsId)
        val m2 = createTestWorkspaceMembership(workspaceId = wsId)
        workspaceMembershipRepo.save(m1)
        workspaceMembershipRepo.save(m2)

        val results = workspaceMembershipRepo.findByWorkspaceId(wsId)

        assertEquals(2, results.size)
    }

    @Test
    fun `customRole save and findById`() {
        val role = createTestCustomRole()
        customRoleRepo.save(role)

        val found = customRoleRepo.findById(role.id)

        assertNotNull(found)
        assertEquals(role.id, found!!.id)
        assertEquals("Editor", found.name)
        assertEquals(mapOf("can_edit" to true, "can_delete" to false), found.permissions)
    }

    @Test
    fun `customRole findByOrganizationId returns roles`() {
        val orgId = UUID.randomUUID()
        val r1 = createTestCustomRole(organizationId = orgId)
        val r2 = createTestCustomRole(organizationId = orgId)
        customRoleRepo.save(r1)
        customRoleRepo.save(r2)

        val results = customRoleRepo.findByOrganizationId(orgId)

        assertEquals(2, results.size)
    }

    @Test
    fun `invitation save and findById`() {
        val invitation = createTestInvitation()
        invitationRepo.save(invitation)

        val found = invitationRepo.findById(invitation.id)

        assertNotNull(found)
        assertEquals(invitation.id, found!!.id)
        assertEquals("test@example.com", found.email)
        assertEquals(OrgRole.MEMBER, found.orgRole)
        assertEquals(InvitationStatus.PENDING, found.status)
    }

    @Test
    fun `invitation findByToken returns invitation`() {
        val invitation = createTestInvitation(token = "unique-token-123")
        invitationRepo.save(invitation)

        val found = invitationRepo.findByToken("unique-token-123")

        assertNotNull(found)
        assertEquals(invitation.id, found!!.id)
    }

    private fun createTestOrganization() = Organization(
        id = UUID.randomUUID(),
        name = "Test Org",
        logoUrl = null,
        defaultTimezone = "UTC",
        billingEmail = "billing@test.com",
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    )

    private fun createTestOrgMembership(
        organizationId: UUID = UUID.randomUUID(),
    ) = OrgMembership(
        id = UUID.randomUUID(),
        userId = UUID.randomUUID(),
        organizationId = organizationId,
        orgRole = OrgRole.MEMBER,
        invitedAt = Instant.now(),
        acceptedAt = null,
    )

    private fun createTestWorkspaceMembership(
        workspaceId: UUID = UUID.randomUUID(),
    ) = WorkspaceMembership(
        id = UUID.randomUUID(),
        userId = UUID.randomUUID(),
        workspaceId = workspaceId,
        workspaceRole = WorkspaceRole.EDITOR,
        customRoleId = null,
        addedAt = Instant.now(),
    )

    private fun createTestCustomRole(
        organizationId: UUID = UUID.randomUUID(),
    ) = CustomRole(
        id = UUID.randomUUID(),
        organizationId = organizationId,
        name = "Editor",
        permissions = mapOf("can_edit" to true, "can_delete" to false),
        createdAt = Instant.now(),
        updatedAt = Instant.now(),
    )

    private fun createTestInvitation(
        token: String = "token-${UUID.randomUUID()}",
    ) = Invitation(
        id = UUID.randomUUID(),
        organizationId = UUID.randomUUID(),
        email = "test@example.com",
        orgRole = OrgRole.MEMBER,
        workspaceAssignments = "[]",
        invitedBy = UUID.randomUUID(),
        token = token,
        expiresAt = Instant.now().plusSeconds(86400),
        acceptedAt = null,
        status = InvitationStatus.PENDING,
        createdAt = Instant.now(),
    )
}
