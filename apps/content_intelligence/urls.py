from django.urls import path

from . import views

app_name = "content_intelligence"
urlpatterns = [
    path("<uuid:brand_id>/strategy/", views.strategy, name="strategy"),
    path("<uuid:brand_id>/plans/new/", views.plan_create, name="plan_create"),
    path("<uuid:brand_id>/plans/<uuid:plan_id>/", views.plan_detail, name="plan_detail"),
    path("<uuid:brand_id>/generate/", views.generate, name="generate"),
    path("<uuid:brand_id>/generated/<uuid:content_id>/", views.generated_detail, name="generated_detail"),
    path(
        "<uuid:brand_id>/generated/<uuid:content_id>/composer/",
        views.create_composer_draft,
        name="create_composer_draft",
    ),
]
