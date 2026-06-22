from django.urls import path

from . import views

app_name = "composer"

urlpatterns = [
    # Create landing page
    path("create/", views.create_landing, name="create_landing"),
    # Idea CRUD (HTMX endpoints)
    path("ideas/upload-media/", views.idea_upload_media, name="idea_upload_media"),
    path("ideas/create/", views.idea_create, name="idea_create"),
    path("ideas/<uuid:idea_id>/create-post/", views.idea_create_post, name="idea_create_post"),
    path("ideas/<uuid:idea_id>/edit/", views.idea_edit, name="idea_edit"),
    path("ideas/<uuid:idea_id>/delete/", views.idea_delete, name="idea_delete"),
    path("ideas/<uuid:idea_id>/move/", views.idea_move, name="idea_move"),
    path("ideas/board/", views.idea_board, name="idea_board"),
    # Idea groups (Kanban columns)
    path("ideas/groups/create/", views.idea_group_create, name="idea_group_create"),
    path("ideas/groups/<uuid:group_id>/delete/", views.idea_group_delete, name="idea_group_delete"),
    path("ideas/groups/reorder/", views.idea_group_reorder, name="idea_group_reorder"),
    # Composer page
    path("compose/", views.compose, name="compose"),
    path("compose/<uuid:post_id>/", views.compose, name="compose_edit"),
    # Save actions
    path("compose/save/", views.save_post, name="save_post"),
    path("compose/<uuid:post_id>/save/", views.save_post, name="save_post_edit"),
    # Per-platform status transition (one PlatformPost at a time)
    path(
        "compose/<uuid:post_id>/platform-posts/<uuid:platform_post_id>/transition/",
        views.transition_platform_post,
        name="transition_platform_post",
    ),
    # Auto-save
    path("compose/autosave/", views.autosave, name="autosave"),
    path("compose/<uuid:post_id>/autosave/", views.autosave, name="autosave_edit"),
    # Live preview
    path("compose/preview/", views.preview, name="preview"),
    # Media
    path("compose/media-picker/", views.media_picker, name="media_picker"),
    path("compose/thumbnail-picker/", views.thumbnail_picker, name="thumbnail_picker"),
    path("compose/thumbnail-upload/", views.thumbnail_upload, name="thumbnail_upload"),
    path("compose/media-stream/<uuid:asset_id>/", views.media_stream, name="media_stream"),
    path("compose/media-filmstrip/<uuid:asset_id>/", views.media_filmstrip, name="media_filmstrip"),
    path("compose/unsplash-search/", views.unsplash_search, name="unsplash_search"),
    path("compose/unsplash-import/", views.unsplash_import, name="unsplash_import"),
    path("compose/<uuid:post_id>/unsplash-import/", views.unsplash_import, name="unsplash_import_post"),
    path("compose/pinterest-boards/<uuid:account_id>/", views.pinterest_boards, name="pinterest_boards"),
    path("compose/tiktok-creator-info/<uuid:account_id>/", views.tiktok_creator_info, name="tiktok_creator_info"),
    path("compose/<uuid:post_id>/media-picker/", views.media_picker, name="media_picker_post"),
    path("compose/<uuid:post_id>/attach-media/", views.attach_media, name="attach_media"),
    path("compose/attach-pending-media/", views.attach_pending_media, name="attach_pending_media"),
    path("compose/upload-media/", views.upload_media, name="upload_media"),
    path("compose/<uuid:post_id>/upload-media/", views.upload_media, name="upload_media_post"),
    path("compose/<uuid:post_id>/remove-media/<uuid:media_id>/", views.remove_media, name="remove_media"),
    path("compose/remove-pending-media/<uuid:asset_id>/", views.remove_pending_media, name="remove_pending_media"),
    # Drafts
    path("drafts/", views.drafts_list, name="drafts_list"),
    # Post delete
    path("compose/<uuid:post_id>/delete/", views.post_delete, name="post_delete"),
    # Clone / Repost
    path("compose/<uuid:post_id>/clone/", views.clone_post_view, name="clone_post"),
    # Content Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<uuid:category_id>/edit/", views.category_edit, name="category_edit"),
    path("categories/<uuid:category_id>/delete/", views.category_delete, name="category_delete"),
    # Post Templates
    path("templates/", views.template_list, name="template_list"),
    path("templates/<uuid:template_id>/delete/", views.template_delete, name="template_delete"),
    path("templates/<uuid:template_id>/use/", views.use_template, name="use_template"),
    path("templates/picker/", views.template_picker, name="template_picker"),
    path("compose/<uuid:post_id>/save-as-template/", views.save_as_template, name="save_as_template"),
    # CSV Import
    path("import/csv/", views.csv_upload, name="csv_upload"),
    path("import/csv/preview/", views.csv_preview, name="csv_preview"),
    path("import/csv/confirm/", views.csv_confirm_import, name="csv_confirm_import"),
    # Tags
    path("tags/", views.tag_list, name="tag_list"),
    path("tags/create/", views.tag_create, name="tag_create"),
    # Feeds
    path("feeds/", views.feed_list, name="feed_list"),
    path("feeds/add/", views.feed_add, name="feed_add"),
    path("feeds/<uuid:feed_id>/delete/", views.feed_delete, name="feed_delete"),
    path("feeds/explore/", views.feed_explore, name="feed_explore"),
]
