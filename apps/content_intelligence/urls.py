from django.urls import path

from . import views

app_name = "content_intelligence"
urlpatterns = [
    path("ai-settings/", views.provider_settings, name="provider_settings"),
    path("library/", views.content_library, name="content_library"),
    path("library/action/", views.content_library_action, name="content_library_action"),
    path("library/bulk/", views.content_library_bulk, name="content_library_bulk"),
    path("campaigns/new/", views.campaign_create, name="campaign_create"),
    path("<uuid:brand_id>/strategy/", views.strategy, name="strategy"),
    path("<uuid:brand_id>/plans/new/", views.plan_create, name="plan_create"),
    path("<uuid:brand_id>/plans/<uuid:plan_id>/", views.plan_detail, name="plan_detail"),
    path(
        "<uuid:brand_id>/plans/<uuid:plan_id>/items/<uuid:item_id>/draft/",
        views.create_plan_item_draft,
        name="create_plan_item_draft",
    ),
    path("<uuid:brand_id>/generate/", views.generate, name="generate"),
    path("<uuid:brand_id>/generations/", views.generation_history, name="generation_history"),
    path("<uuid:brand_id>/generations/<uuid:request_id>/", views.generation_request_detail, name="generation_request_detail"),
    path("<uuid:brand_id>/generations/<uuid:request_id>/retry/", views.retry_generation, name="retry_generation"),
    path("<uuid:brand_id>/generated/<uuid:content_id>/", views.generated_detail, name="generated_detail"),
    path("<uuid:brand_id>/visuals/new/", views.visual_brief_create, name="visual_brief_create"),
    path("<uuid:brand_id>/visuals/", views.visual_brief_history, name="visual_brief_history"),
    path("<uuid:brand_id>/visuals/<uuid:brief_id>/", views.visual_brief_detail, name="visual_brief_detail"),
    path("<uuid:brand_id>/visuals/<uuid:brief_id>/retry/", views.visual_brief_retry, name="visual_brief_retry"),
    path(
        "<uuid:brand_id>/generated/<uuid:content_id>/composer/",
        views.create_composer_draft,
        name="create_composer_draft",
    ),
]
