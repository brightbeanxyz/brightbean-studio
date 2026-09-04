from django.urls import path

from . import views

app_name = "content_intelligence"
urlpatterns = [
    path("ai-settings/", views.provider_settings, name="provider_settings"),
    path("<uuid:brand_id>/strategy/", views.strategy, name="strategy"),
    path("<uuid:brand_id>/plans/new/", views.plan_create, name="plan_create"),
    path("<uuid:brand_id>/plans/<uuid:plan_id>/", views.plan_detail, name="plan_detail"),
    path("<uuid:brand_id>/generate/", views.generate, name="generate"),
    path("<uuid:brand_id>/generations/", views.generation_history, name="generation_history"),
    path("<uuid:brand_id>/generations/<uuid:request_id>/", views.generation_request_detail, name="generation_request_detail"),
    path("<uuid:brand_id>/generations/<uuid:request_id>/retry/", views.retry_generation, name="retry_generation"),
    path("<uuid:brand_id>/generated/<uuid:content_id>/", views.generated_detail, name="generated_detail"),
    path(
        "<uuid:brand_id>/generated/<uuid:content_id>/composer/",
        views.create_composer_draft,
        name="create_composer_draft",
    ),
]
