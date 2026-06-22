from django.urls import path

from . import views

app_name = "calendar"

urlpatterns = [
    # Main calendar view
    path("", views.calendar_view, name="calendar"),
    # Drag-and-drop reschedule
    path("reschedule/", views.reschedule_post, name="reschedule"),
    # Posting slots
    path("posting-slots/", views.posting_slots, name="posting_slots"),
    path("posting-slots/save/", views.save_posting_slot, name="save_posting_slot"),
    path("posting-slots/grid/", views.account_posting_slots_partial, name="account_slots_partial"),
    path("posting-slots/toggle-day/", views.toggle_posting_slot_day, name="toggle_posting_slot_day"),
    path("posting-slots/<uuid:slot_id>/delete/", views.delete_posting_slot, name="delete_posting_slot"),
    path("posting-slots/<uuid:slot_id>/update/", views.update_posting_slot, name="update_posting_slot"),
    # Queues
    path("queues/", views.queue_list, name="queue_list"),
    path("queues/create/", views.queue_create, name="queue_create"),
    path("queues/<uuid:queue_id>/", views.queue_detail, name="queue_detail"),
    path("queues/<uuid:queue_id>/delete/", views.queue_delete, name="queue_delete"),
    path("queues/<uuid:queue_id>/reorder/", views.queue_reorder, name="queue_reorder"),
    path(
        "queues/<uuid:queue_id>/entries/<uuid:entry_id>/remove/",
        views.queue_entry_remove,
        name="queue_entry_remove",
    ),
    path(
        "queues/<uuid:queue_id>/entries/<uuid:entry_id>/reslot/",
        views.queue_entry_reslot,
        name="queue_entry_reslot",
    ),
    # Publish page tab partials (HTMX)
    path("publish/queue/", views.publish_tab_queue, name="publish_tab_queue"),
    path("publish/drafts/", views.publish_tab_drafts, name="publish_tab_drafts"),
    path("publish/approvals/", views.publish_tab_approvals, name="publish_tab_approvals"),
    path("publish/sent/", views.publish_tab_sent, name="publish_tab_sent"),
    # Custom Calendar Events
    path("events/create/", views.event_create, name="event_create"),
    path("events/<uuid:event_id>/edit/", views.event_edit, name="event_edit"),
    path("events/<uuid:event_id>/delete/", views.event_delete, name="event_delete"),
]
