"""Content Calendar models (F-2.3) - scheduling, time slots, queues, and events."""

import uuid

from django.conf import settings
from django.db import models

from apps.common.managers import WorkspaceScopedManager
from apps.common.validators import validate_hex_color


class PostingSlot(models.Model):
    """Recurring time slot for a social account.

    Defines default publishing times (e.g., Mon/Wed/Fri at 9 AM)
    used for queue-based scheduling.
    """

    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    social_account = models.ForeignKey(
        "social_accounts.SocialAccount",
        on_delete=models.CASCADE,
        related_name="posting_slots",
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices)
    time = models.TimeField(help_text="Posting time (in workspace timezone).")
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "calendar_posting_slot"
        ordering = ["day_of_week", "time"]
        unique_together = [("social_account", "day_of_week", "time")]

    def __str__(self):
        return f"{self.get_day_of_week_display()} @ {self.time.strftime('%H:%M')} ({self.social_account})"

    @property
    def day_name(self):
        return self.get_day_of_week_display()


class Queue(models.Model):
    """A named publishing queue that maps posts to time slots.

    Each queue is tied to a workspace and optionally to a content category
    and social account. Posts added to a queue are auto-assigned to the
    next available PostingSlot datetime.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="queues",
    )
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        "composer.ContentCategory",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="queues",
    )
    social_account = models.ForeignKey(
        "social_accounts.SocialAccount",
        on_delete=models.CASCADE,
        related_name="queues",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "calendar_queue"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.social_account})"


class QueueEntry(models.Model):
    """A post's position within a queue, with its assigned publish slot."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    queue = models.ForeignKey(
        Queue,
        on_delete=models.CASCADE,
        related_name="entries",
    )
    post = models.ForeignKey(
        "composer.Post",
        on_delete=models.CASCADE,
        related_name="queue_entries",
    )
    position = models.PositiveIntegerField(default=0)
    assigned_slot_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The computed publish datetime from the queue's posting slots.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calendar_queue_entry"
        ordering = ["position"]
        unique_together = [("queue", "post")]

    def __str__(self):
        return f"QueueEntry(pos={self.position}): {self.post_id} in {self.queue.name}"


class RecurrenceRule(models.Model):
    """Defines how a post recurs (daily, weekly, monthly).

    The background task generates individual Post records for each
    recurrence up to 90 days ahead.
    """

    class Frequency(models.TextChoices):
        DAILY = "daily", "Daily"
        WEEKLY = "weekly", "Weekly"
        MONTHLY = "monthly", "Monthly"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.OneToOneField(
        "composer.Post",
        on_delete=models.CASCADE,
        related_name="recurrence_rule",
    )
    frequency = models.CharField(max_length=10, choices=Frequency.choices)
    interval = models.PositiveIntegerField(
        default=1,
        help_text="Repeat every N frequency units (e.g., every 2 weeks).",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="Stop generating recurrences after this date. Null = indefinite.",
    )
    last_generated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last recurrence generation run.",
    )
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "calendar_recurrence_rule"

    def __str__(self):
        return f"RecurrenceRule({self.frequency} every {self.interval}) for {self.post_id}"


class CustomCalendarEvent(models.Model):
    """Custom event on the workspace calendar (e.g., product launch, campaign start).

    Displayed as full-width colored bars spanning start_date to end_date.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="calendar_events",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    start_date = models.DateField()
    end_date = models.DateField()
    color = models.CharField(
        max_length=7,
        default="#3B82F6",
        help_text="Hex color for the event bar.",
        validators=[validate_hex_color],
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WorkspaceScopedManager()

    class Meta:
        db_table = "calendar_custom_event"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.title} ({self.start_date} – {self.end_date})"
