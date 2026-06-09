import datetime
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from apps.notifications.engine import notify
from apps.notifications.models import (
    Channel,
    DeliveryStatus,
    EventType,
    Notification,
    NotificationDelivery,
    NotificationPreference,
    QuietHours,
)


@pytest.mark.django_db
class TestNotifyEngine:
    """Tests for the core notify() function."""

    def test_creates_notification(self, user):
        n = notify(user, EventType.POST_APPROVED, "Post approved", "Your post was approved.")
        assert n is not None
        assert n.user == user
        assert n.event_type == EventType.POST_APPROVED
        assert n.title == "Post approved"
        assert n.body == "Your post was approved."
        assert n.is_read is False

    def test_creates_deliveries_for_default_channels(self, user):
        notify(user, EventType.POST_APPROVED, "Post approved")
        deliveries = NotificationDelivery.objects.filter(notification__user=user)
        # POST_APPROVED defaults: in_app=True, email=False
        channels = set(deliveries.values_list("channel", flat=True))
        assert Channel.IN_APP in channels
        assert Channel.EMAIL not in channels

    def test_respects_user_preference_override(self, user):
        # Disable in-app, enable email
        NotificationPreference.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            channel=Channel.IN_APP,
            is_enabled=False,
        )
        NotificationPreference.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            channel=Channel.EMAIL,
            is_enabled=True,
        )

        notify(user, EventType.POST_APPROVED, "Post approved")
        deliveries = NotificationDelivery.objects.filter(notification__user=user)
        channels = set(deliveries.values_list("channel", flat=True))
        assert Channel.IN_APP not in channels
        assert Channel.EMAIL in channels

    def test_returns_none_for_inactive_user(self, user):
        user.is_active = False
        user.save()
        result = notify(user, EventType.POST_APPROVED, "Test")
        assert result is None

    def test_returns_none_for_unknown_event_type(self, user):
        result = notify(user, "totally_unknown", "Test")
        assert result is None

    def test_stores_data_json(self, user):
        data = {"post_id": "abc-123", "workspace_id": "ws-456"}
        n = notify(user, EventType.POST_PUBLISHED, "Published", data=data)
        assert n.data == data

    def test_in_app_delivery_marked_delivered(self, user):
        notify(user, EventType.POST_APPROVED, "Approved")
        delivery = NotificationDelivery.objects.get(notification__user=user, channel=Channel.IN_APP)
        assert delivery.status == DeliveryStatus.DELIVERED

    def test_quiet_hours_suppresses_non_critical(self, user):
        QuietHours.objects.create(
            user=user,
            is_enabled=True,
            start_time=datetime.time(0, 0),
            end_time=datetime.time(23, 59),
            timezone="UTC",
        )
        notify(user, EventType.POST_PUBLISHED, "Published")
        # POST_PUBLISHED is non-critical, during quiet hours only in-app should be delivered
        deliveries = NotificationDelivery.objects.filter(notification__user=user)
        for d in deliveries:
            assert d.channel == Channel.IN_APP

    def test_quiet_hours_does_not_suppress_critical(self, user):
        QuietHours.objects.create(
            user=user,
            is_enabled=True,
            start_time=datetime.time(0, 0),
            end_time=datetime.time(23, 59),
            timezone="UTC",
        )
        # Enable email for POST_FAILED (critical event)
        NotificationPreference.objects.create(
            user=user,
            event_type=EventType.POST_FAILED,
            channel=Channel.EMAIL,
            is_enabled=True,
        )
        notify(user, EventType.POST_FAILED, "Post failed")
        channels = set(NotificationDelivery.objects.filter(notification__user=user).values_list("channel", flat=True))
        # POST_FAILED is critical - email should not be suppressed
        assert Channel.EMAIL in channels


@pytest.mark.django_db
class TestNotificationModel:
    def test_mark_as_read(self, user):
        n = Notification.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            title="Test",
            is_read=False,
        )
        assert n.is_read is False
        n.is_read = True
        n.read_at = timezone.now()
        n.save()
        n.refresh_from_db()
        assert n.is_read is True
        assert n.read_at is not None

    def test_notification_ordering(self, user):
        Notification.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            title="First",
        )
        n2 = Notification.objects.create(
            user=user,
            event_type=EventType.POST_PUBLISHED,
            title="Second",
        )
        notifications = list(Notification.objects.filter(user=user))
        assert notifications[0].id == n2.id  # newest first


@pytest.mark.django_db
class TestNotificationViews:
    def test_unread_count_endpoint(self, client, user):
        client.force_login(user)
        Notification.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            title="Test",
            is_read=False,
        )
        Notification.objects.create(
            user=user,
            event_type=EventType.POST_PUBLISHED,
            title="Test 2",
            is_read=True,
        )
        response = client.get("/notifications/unread-count/")
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_mark_as_read_endpoint(self, client, user):
        client.force_login(user)
        n = Notification.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            title="Test",
            is_read=False,
        )
        response = client.post(f"/notifications/{n.id}/read/")
        assert response.status_code == 200
        n.refresh_from_db()
        assert n.is_read is True

    def test_mark_all_read_endpoint(self, client, user):
        client.force_login(user)
        for i in range(3):
            Notification.objects.create(
                user=user,
                event_type=EventType.POST_APPROVED,
                title=f"Test {i}",
                is_read=False,
            )
        response = client.post("/notifications/mark-all-read/")
        assert response.status_code == 200
        assert Notification.objects.filter(user=user, is_read=False).count() == 0

    def test_notification_list_page(self, client, user):
        client.force_login(user)
        response = client.get("/notifications/")
        assert response.status_code == 200

    def test_notification_list_filter_by_event_type(self, client, user):
        client.force_login(user)
        Notification.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            title="Approved",
        )
        Notification.objects.create(
            user=user,
            event_type=EventType.POST_FAILED,
            title="Failed",
        )
        response = client.get("/notifications/?event_type=post_approved")
        assert response.status_code == 200

    def test_preferences_page_get(self, client, user):
        client.force_login(user)
        response = client.get("/notifications/preferences/")
        assert response.status_code == 200

    def test_preferences_page_post(self, client, user):
        client.force_login(user)
        response = client.post(
            "/notifications/preferences/",
            {
                "pref_post_approved_in_app": "on",
                "pref_post_approved_email": "on",
                "quiet_hours_timezone": "America/New_York",
            },
        )
        assert response.status_code == 302
        pref = NotificationPreference.objects.get(
            user=user,
            event_type=EventType.POST_APPROVED,
            channel=Channel.IN_APP,
        )
        assert pref.is_enabled is True


@pytest.mark.django_db
class TestWebhookDispatchSSRFGuard:
    """The webhook dispatcher must reject private / loopback URLs.

    Regression: pre-fix the code POSTed via urllib.request.urlopen with no URL
    validation, so a notification stored with webhook_url=http://127.0.0.1:6379/
    would hit local services.
    """

    def _build_delivery(self, user, webhook_url):
        notification = Notification.objects.create(
            user=user,
            event_type=EventType.POST_APPROVED,
            title="t",
            body="b",
            data={"webhook_url": webhook_url},
        )
        return NotificationDelivery.objects.create(
            notification=notification,
            channel=Channel.WEBHOOK,
            status=DeliveryStatus.PENDING,
        )

    def test_rejects_loopback_url(self, user):
        from apps.notifications.engine import _dispatch_webhook

        with (
            patch("httpx.post") as httpx_post,
            patch("socket.getaddrinfo", return_value=[(0, 0, 0, "", ("127.0.0.1", 0))]),
        ):
            delivery = self._build_delivery(user, "http://localhost/")
            with pytest.raises(RuntimeError, match="rejected"):
                _dispatch_webhook(delivery)
            httpx_post.assert_not_called()

    def test_rejects_private_ip(self, user):
        from apps.notifications.engine import _dispatch_webhook

        with (
            patch("httpx.post") as httpx_post,
            patch("socket.getaddrinfo", return_value=[(0, 0, 0, "", ("10.0.0.5", 0))]),
        ):
            delivery = self._build_delivery(user, "http://internal-svc.example.com/")
            with pytest.raises(RuntimeError, match="rejected"):
                _dispatch_webhook(delivery)
            httpx_post.assert_not_called()

    def test_rejects_file_scheme(self, user):
        from apps.notifications.engine import _dispatch_webhook

        with patch("httpx.post") as httpx_post:
            delivery = self._build_delivery(user, "file:///etc/passwd")
            with pytest.raises(RuntimeError, match="rejected"):
                _dispatch_webhook(delivery)
            httpx_post.assert_not_called()

    def test_accepts_public_url(self, user):
        from apps.notifications.engine import _dispatch_webhook

        mock_response = Mock(status_code=200)
        with (
            patch("socket.getaddrinfo", return_value=[(0, 0, 0, "", ("8.8.8.8", 0))]),
            patch("httpx.post", return_value=mock_response) as httpx_post,
        ):
            delivery = self._build_delivery(user, "https://hooks.example.com/abc")
            _dispatch_webhook(delivery)
            httpx_post.assert_called_once()
