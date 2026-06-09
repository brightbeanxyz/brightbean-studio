package com.brightbean.studio.application.service

import com.brightbean.studio.domain.model.DeliveryStatus
import com.brightbean.studio.domain.model.EventType
import com.brightbean.studio.domain.model.Notification
import com.brightbean.studio.domain.model.NotificationChannel
import com.brightbean.studio.domain.model.NotificationDelivery
import com.brightbean.studio.domain.model.NotificationPreference
import com.brightbean.studio.domain.model.QuietHours
import com.brightbean.studio.domain.repository.NotificationDeliveryRepository
import com.brightbean.studio.domain.repository.NotificationPreferenceRepository
import com.brightbean.studio.domain.repository.NotificationRepository
import com.brightbean.studio.domain.repository.QuietHoursRepository
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertNotNull
import org.junit.jupiter.api.BeforeEach
import org.junit.jupiter.api.Test
import java.time.Instant
import java.time.LocalTime
import java.util.UUID

class NotificationEngineTest {

    private lateinit var notifRepo: InMemNotifRepo
    private lateinit var prefRepo: InMemPrefRepo
    private lateinit var deliveryRepo: InMemDeliveryRepo
    private lateinit var qhRepo: InMemQHRepo
    private lateinit var engine: NotificationEngine

    @BeforeEach
    fun setUp() {
        notifRepo = InMemNotifRepo()
        prefRepo = InMemPrefRepo()
        deliveryRepo = InMemDeliveryRepo()
        qhRepo = InMemQHRepo()
        engine = NotificationEngine(notifRepo, prefRepo, deliveryRepo, qhRepo)
    }

    @Test
    fun `notify creates notification with IN_APP by default`() {
        val userId = UUID.randomUUID()
        val n = engine.notify(userId, EventType.POST_PUBLISHED, "Post published", "Your post was published")

        assertNotNull(n)
        assertEquals(userId, n.userId)
        assertEquals(EventType.POST_PUBLISHED, n.eventType)
        assertEquals(1, deliveryRepo.items.size)
        assertEquals(NotificationChannel.IN_APP, deliveryRepo.items.first().channel)
    }

    @Test
    fun `notify uses preferences to determine channels`() {
        val userId = UUID.randomUUID()
        prefRepo.save(NotificationPreference(UUID.randomUUID(), userId, EventType.POST_FAILED, NotificationChannel.EMAIL, true))
        prefRepo.save(NotificationPreference(UUID.randomUUID(), userId, EventType.POST_FAILED, NotificationChannel.IN_APP, true))

        engine.notify(userId, EventType.POST_FAILED, "Post failed", "Error")

        assertEquals(2, deliveryRepo.items.size)
    }

    @Test
    fun `sendInvitation sends notification`() {
        val inviterId = UUID.randomUUID()
        engine.sendInvitation("test@test.com", UUID.randomUUID(), inviterId)
        assertEquals(1, notifRepo.items.size)
    }
}

class NotificationUseCasesTest {

    private lateinit var notifRepo: InMemNotifRepo
    private lateinit var prefRepo: InMemPrefRepo
    private lateinit var qhRepo: InMemQHRepo
    private lateinit var useCases: NotificationUseCases

    @BeforeEach
    fun setUp() {
        notifRepo = InMemNotifRepo()
        prefRepo = InMemPrefRepo()
        qhRepo = InMemQHRepo()
        useCases = NotificationUseCases(notifRepo, prefRepo, qhRepo)
    }

    @Test
    fun `markAsRead marks notification as read`() {
        val n = createNotification()
        notifRepo.save(n)

        val updated = useCases.markAsRead(n.id)
        assertNotNull(updated)
        assertEquals(true, updated!!.isRead)
    }

    @Test
    fun `getUnreadCount returns correct count`() {
        val userId = UUID.randomUUID()
        notifRepo.save(createNotification(userId = userId, isRead = false))
        notifRepo.save(createNotification(userId = userId, isRead = false))
        notifRepo.save(createNotification(userId = userId, isRead = true))

        assertEquals(2, useCases.getUnreadCount(userId))
    }

    @Test
    fun `markAllRead marks all notifications for user`() {
        val userId = UUID.randomUUID()
        notifRepo.save(createNotification(userId = userId, isRead = false))
        notifRepo.save(createNotification(userId = userId, isRead = false))

        useCases.markAllRead(userId)
        assertEquals(2, notifRepo.items.count { it.userId == userId && it.isRead })
    }

    @Test
    fun `quietHours save and retrieve`() {
        val userId = UUID.randomUUID()
        val qh = QuietHours(UUID.randomUUID(), userId, true, LocalTime.of(22, 0), LocalTime.of(8, 0), "UTC", true)

        useCases.updateQuietHours(qh)
        val found = useCases.getQuietHours(userId)
        assertNotNull(found)
        assertEquals(LocalTime.of(22, 0), found!!.startTime)
    }

    private fun createNotification(
        userId: UUID = UUID.randomUUID(),
        isRead: Boolean = false,
    ) = Notification(
        id = UUID.randomUUID(),
        userId = userId,
        eventType = EventType.POST_PUBLISHED,
        title = "Test",
        body = "Test body",
        data = null,
        isRead = isRead,
        readAt = null,
        createdAt = Instant.now(),
    )
}

class InMemNotifRepo : NotificationRepository {
    val items = mutableListOf<Notification>()
    override fun findById(id: UUID) = items.find { it.id == id }
    override fun findByUserId(userId: UUID) = items.filter { it.userId == userId }
    override fun findUnreadByUserId(userId: UUID) = items.filter { it.userId == userId && !it.isRead }
    override fun countUnreadByUserId(userId: UUID) = items.count { it.userId == userId && !it.isRead }
    override fun save(n: Notification) = n.also { items.add(it) }
    override fun update(n: Notification) = n.also { items.removeAll { it.id == n.id }; items.add(it) }
    override fun markAllReadByUserId(userId: UUID) { items.replaceAll { if (it.userId == userId && !it.isRead) it.copy(isRead = true, readAt = Instant.now()) else it } }
}

class InMemPrefRepo : NotificationPreferenceRepository {
    private val items = mutableListOf<NotificationPreference>()
    override fun findByUserId(userId: UUID) = items.filter { it.userId == userId }
    override fun save(p: NotificationPreference) = p.also { items.add(it) }
    override fun update(p: NotificationPreference) = p.also { items.replaceAll { if (it.id == p.id) p else it } }
}

class InMemDeliveryRepo : NotificationDeliveryRepository {
    val items = mutableListOf<NotificationDelivery>()
    override fun findByNotificationId(notificationId: UUID) = items.filter { it.notificationId == notificationId }
    override fun save(d: NotificationDelivery) = d.also { items.add(it) }
    override fun update(d: NotificationDelivery) = d.also { items.replaceAll { if (it.id == d.id) d else it } }
    override fun findPending() = items.filter { it.status == DeliveryStatus.PENDING }
}

class InMemQHRepo : QuietHoursRepository {
    private val items = mutableMapOf<UUID, QuietHours>()
    override fun findByUserId(userId: UUID) = items[userId]
    override fun save(qh: QuietHours) = qh.also { items[qh.userId] = it }
    override fun update(qh: QuietHours) = qh.also { items[qh.userId] = it }
}
