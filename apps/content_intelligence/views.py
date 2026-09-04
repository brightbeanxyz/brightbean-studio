import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods, require_POST

from apps.brands.forms import EditorialStrategyForm
from apps.brands.models import BrandProfile, EditorialStrategy
from apps.brands.services import save_editorial_strategy

from .forms import AIProviderConfigurationForm, CampaignForm, ContentPlanForm, GenerationForm, VisualBriefForm
from .generation import configured_providers, queue_generation
from .generation import create_composer_draft as create_composer_draft_service
from .models import AIProviderConfiguration, Campaign, ContentPlan, GeneratedContent, GenerationRequest, VisualBrief
from .providers import ProviderError
from .services import create_content_plan
from .visuals import image_provider_configurations, queue_visual_brief


def _can_manage(request):
    return bool(request.workspace_membership.effective_permissions.get("manage_editorial_strategy", False))


def _get_brand(request, brand_id):
    try:
        return BrandProfile.objects.get(id=brand_id, workspace=request.workspace)
    except BrandProfile.DoesNotExist:
        raise Http404 from None


@login_required
@require_http_methods(["GET", "POST"])
def strategy(request, workspace_id, brand_id):
    brand = _get_brand(request, brand_id)
    try:
        current = brand.editorial_strategy
    except EditorialStrategy.DoesNotExist:
        current = EditorialStrategy(brand=brand)
    if request.method == "POST" and not _can_manage(request):
        raise PermissionDenied("Permission denied: manage_editorial_strategy")
    form = EditorialStrategyForm(request.POST or None, instance=current)
    if request.method == "POST" and form.is_valid():
        saved, version = save_editorial_strategy(brand=brand, data=form.cleaned_data, user=request.user)
        messages.success(request, f"Editorial strategy saved as version {version.version}.")
        return redirect("content_intelligence:strategy", workspace_id=request.workspace.id, brand_id=brand.id)
    plans = ContentPlan.objects.filter(workspace=request.workspace, brand=brand).prefetch_related("items")
    return render(
        request,
        "content_intelligence/strategy.html",
        {
            "workspace": request.workspace,
            "brand": brand,
            "form": form,
            "strategy": current,
            "plans": plans,
            "can_manage_strategy": _can_manage(request),
            "settings_active": "brands",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def plan_create(request, workspace_id, brand_id):
    if not _can_manage(request):
        raise PermissionDenied("Permission denied: manage_editorial_strategy")
    brand = _get_brand(request, brand_id)
    form = ContentPlanForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        plan = create_content_plan(
            brand=brand,
            cadence=form.cleaned_data["cadence"],
            start_date=form.cleaned_data["start_date"],
            user=request.user,
        )
        messages.success(request, f"{plan.get_cadence_display()} content plan generated.")
        return redirect(
            "content_intelligence:plan_detail", workspace_id=request.workspace.id, brand_id=brand.id, plan_id=plan.id
        )
    return render(
        request,
        "content_intelligence/plan_form.html",
        {"workspace": request.workspace, "brand": brand, "form": form, "settings_active": "brands"},
    )


@login_required
def plan_detail(request, workspace_id, brand_id, plan_id):
    brand = _get_brand(request, brand_id)
    try:
        plan = (
            ContentPlan.objects.select_related("strategy_version")
            .prefetch_related("items")
            .get(id=plan_id, workspace=request.workspace, brand=brand)
        )
    except ContentPlan.DoesNotExist:
        raise Http404 from None
    return render(
        request,
        "content_intelligence/plan_detail.html",
        {"workspace": request.workspace, "brand": brand, "plan": plan, "settings_active": "brands"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def generate(request, workspace_id, brand_id):
    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    brand = _get_brand(request, brand_id)
    configurations = list(configured_providers(request.workspace.organization))
    provider_choices = [(item.provider, item.get_provider_display()) for item in configurations]
    form = GenerationForm(request.POST or None, provider_choices=provider_choices)
    if request.method == "POST" and form.is_valid():
        try:
            generation_request = queue_generation(
                brand=brand,
                provider=form.cleaned_data["provider"],
                platform=form.cleaned_data["platform"],
                content_type=form.cleaned_data["content_type"],
                user=request.user,
                model=form.cleaned_data["model"].strip(),
                audience=form.cleaned_data["audience"].strip(),
                instruction=form.cleaned_data["instruction"].strip(),
            )
        except (ProviderError, ValueError) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Generation queued. This page updates when the draft is ready.")
            return redirect(
                "content_intelligence:generation_request_detail",
                workspace_id=request.workspace.id,
                brand_id=brand.id,
                request_id=generation_request.id,
            )
    return render(
        request,
        "content_intelligence/generate.html",
        {
            "workspace": request.workspace,
            "brand": brand,
            "form": form,
            "has_configured_providers": bool(configurations),
            "settings_active": "brands",
        },
    )


@login_required
def generated_detail(request, workspace_id, brand_id, content_id):
    brand = _get_brand(request, brand_id)
    try:
        output = GeneratedContent.objects.select_related("request").get(
            id=content_id, workspace=request.workspace, brand=brand
        )
    except GeneratedContent.DoesNotExist:
        raise Http404 from None
    return render(
        request,
        "content_intelligence/generated_detail.html",
        {"workspace": request.workspace, "brand": brand, "output": output, "settings_active": "brands"},
    )


@login_required
def generation_history(request, workspace_id, brand_id):
    brand = _get_brand(request, brand_id)
    requests = GenerationRequest.objects.filter(workspace=request.workspace, brand=brand).prefetch_related("outputs")[:100]
    return render(request, "content_intelligence/generation_history.html", {"workspace": request.workspace, "brand": brand, "generation_requests": requests, "settings_active": "brands"})


@login_required
def generation_request_detail(request, workspace_id, brand_id, request_id):
    brand = _get_brand(request, brand_id)
    try:
        generation_request = GenerationRequest.objects.prefetch_related("outputs").get(
            id=request_id, workspace=request.workspace, brand=brand
        )
    except GenerationRequest.DoesNotExist:
        raise Http404 from None
    output = generation_request.outputs.first()
    if output:
        return redirect("content_intelligence:generated_detail", workspace_id=request.workspace.id, brand_id=brand.id, content_id=output.id)
    return render(request, "content_intelligence/generation_request_detail.html", {"workspace": request.workspace, "brand": brand, "generation_request": generation_request, "settings_active": "brands"})


@login_required
@require_POST
def retry_generation(request, workspace_id, brand_id, request_id):
    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    brand = _get_brand(request, brand_id)
    try:
        previous = GenerationRequest.objects.get(id=request_id, workspace=request.workspace, brand=brand)
    except GenerationRequest.DoesNotExist:
        raise Http404 from None
    context = previous.context or {}
    retried = queue_generation(
        brand=brand,
        provider=previous.provider,
        platform=previous.platform,
        content_type=previous.content_type,
        user=request.user,
        model=previous.model,
        audience=previous.audience,
        instruction=context.get("instruction", ""),
        previous_content=context.get("previous_content", []),
        analytics=context.get("analytics", {}),
    )
    messages.success(request, "Generation queued again.")
    return redirect(
        "content_intelligence:generation_request_detail",
        workspace_id=request.workspace.id,
        brand_id=brand.id,
        request_id=retried.id,
    )


@login_required
@require_http_methods(["GET", "POST"])
def provider_settings(request, workspace_id):
    if not request.workspace_membership.effective_permissions.get("manage_workspace_settings", False):
        raise PermissionDenied("Permission denied: manage_workspace_settings")
    provider = request.POST.get("provider") if request.method == "POST" else request.GET.get("provider", "openai")
    if provider not in GenerationRequest.Provider.values:
        raise Http404
    configuration, _ = AIProviderConfiguration.objects.get_or_create(
        organization=request.workspace.organization, provider=provider
    )
    old_key = configuration.api_key
    form = AIProviderConfigurationForm(request.POST or None, instance=configuration)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if not form.cleaned_data["api_key"]:
            saved.api_key = old_key
        if not form.errors:
            saved.save()
            messages.success(request, f"{configuration.get_provider_display()} settings saved.")
            return redirect(f"{request.path}?provider={provider}")
    return render(request, "content_intelligence/provider_settings.html", {"workspace": request.workspace, "configuration": configuration, "form": form, "providers": GenerationRequest.Provider.choices, "settings_active": "brands"})


@login_required
@require_POST
def create_composer_draft(request, workspace_id, brand_id, content_id):
    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    brand = _get_brand(request, brand_id)
    try:
        output = GeneratedContent.objects.get(id=content_id, workspace=request.workspace, brand=brand)
    except GeneratedContent.DoesNotExist:
        raise Http404 from None
    post, created = create_composer_draft_service(output=output, user=request.user)
    if created:
        messages.success(request, "AI draft moved to Composer for review.")
    return redirect("composer:compose_edit", workspace_id=request.workspace.id, post_id=post.id)


@login_required
@require_http_methods(["GET", "POST"])
def visual_brief_create(request, workspace_id, brand_id):
    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    brand = _get_brand(request, brand_id)
    configurations = image_provider_configurations(request.workspace.organization)
    provider_choices = [(item.provider, item.get_provider_display()) for item in configurations]
    output = None
    output_id = request.POST.get("generated_content") or request.GET.get("generated_content")
    if output_id:
        try:
            output = GeneratedContent.objects.select_related("composer_post").get(
                id=output_id, workspace=request.workspace, brand=brand
            )
        except (GeneratedContent.DoesNotExist, ValueError):
            raise Http404 from None
    form = VisualBriefForm(request.POST or None, provider_choices=provider_choices)
    if request.method == "POST" and form.is_valid():
        brief = form.save(commit=False)
        brief.workspace = request.workspace
        brief.brand = brand
        brief.generated_content = output
        brief.generation_request = output.request if output else None
        brief.post = output.composer_post if output else None
        brief.requested_by = request.user
        brief.save()
        try:
            queue_visual_brief(brief=brief)
        except (AIProviderConfiguration.DoesNotExist, ValueError) as exc:
            brief.delete()
            messages.error(request, str(exc))
        else:
            messages.success(request, "Visual generation queued for human review.")
            return redirect(
                "content_intelligence:visual_brief_detail",
                workspace_id=request.workspace.id,
                brand_id=brand.id,
                brief_id=brief.id,
            )
    return render(request, "content_intelligence/visual_brief_form.html", {"workspace": request.workspace, "brand": brand, "form": form, "output": output, "has_configured_providers": bool(configurations), "settings_active": "brands"})


@login_required
def visual_brief_detail(request, workspace_id, brand_id, brief_id):
    brand = _get_brand(request, brand_id)
    try:
        brief = VisualBrief.objects.select_related("media_asset", "post").get(
            id=brief_id, workspace=request.workspace, brand=brand
        )
    except VisualBrief.DoesNotExist:
        raise Http404 from None
    return render(request, "content_intelligence/visual_brief_detail.html", {"workspace": request.workspace, "brand": brand, "brief": brief, "settings_active": "brands"})


@login_required
def visual_brief_history(request, workspace_id, brand_id):
    brand = _get_brand(request, brand_id)
    briefs = VisualBrief.objects.filter(workspace=request.workspace, brand=brand).select_related("media_asset")[:100]
    return render(request, "content_intelligence/visual_brief_history.html", {"workspace": request.workspace, "brand": brand, "briefs": briefs, "settings_active": "brands"})


@login_required
@require_POST
def visual_brief_retry(request, workspace_id, brand_id, brief_id):
    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    brand = _get_brand(request, brand_id)
    try:
        previous = VisualBrief.objects.get(id=brief_id, workspace=request.workspace, brand=brand)
    except VisualBrief.DoesNotExist:
        raise Http404 from None
    brief = VisualBrief.objects.create(
        workspace=request.workspace, brand=brand, generation_request=previous.generation_request,
        generated_content=previous.generated_content, post=previous.post, provider=previous.provider,
        model=previous.model, objective=previous.objective, style=previous.style, format=previous.format,
        colors=previous.colors, constraints=previous.constraints, requested_by=request.user,
    )
    try:
        queue_visual_brief(brief=brief)
    except (AIProviderConfiguration.DoesNotExist, ValueError) as exc:
        brief.delete()
        messages.error(request, str(exc))
        return redirect("content_intelligence:visual_brief_detail", workspace_id=request.workspace.id, brand_id=brand.id, brief_id=previous.id)
    return redirect("content_intelligence:visual_brief_detail", workspace_id=request.workspace.id, brand_id=brand.id, brief_id=brief.id)


def _library_filters(request, posts, generated):
    brand = request.GET.get("brand", "")
    campaign = request.GET.get("campaign", "")
    platform = request.GET.get("platform", "")
    origin = request.GET.get("origin", "")
    status = request.GET.get("status", "")
    archived = request.GET.get("archived", "active")
    date_from = request.GET.get("from", "")
    date_to = request.GET.get("to", "")
    if brand and _is_uuid(brand):
        posts, generated = posts.filter(brand_id=brand), generated.filter(brand_id=brand)
    elif brand:
        posts, generated = posts.none(), generated.none()
    if campaign and _is_uuid(campaign):
        posts, generated = posts.filter(campaign_id=campaign), generated.filter(campaign_id=campaign)
    elif campaign:
        posts, generated = posts.none(), generated.none()
    if platform:
        posts = posts.filter(platform_posts__social_account__platform=platform).distinct()
        generated = generated.filter(platform=platform)
    if origin:
        posts = posts.filter(origin=origin)
        if origin != "ai":
            generated = generated.none()
    if status:
        posts = posts.filter(platform_posts__status=status).distinct()
        generated = generated.filter(status=status)
    if archived == "archived":
        posts, generated = posts.filter(archived_at__isnull=False), generated.filter(archived_at__isnull=False)
    elif archived == "all":
        pass
    else:
        posts, generated = posts.filter(archived_at__isnull=True), generated.filter(archived_at__isnull=True)
    if parse_date(date_from):
        posts, generated = posts.filter(created_at__date__gte=date_from), generated.filter(created_at__date__gte=date_from)
    if parse_date(date_to):
        posts, generated = posts.filter(created_at__date__lte=date_to), generated.filter(created_at__date__lte=date_to)
    return posts, generated


def _is_uuid(value):
    try:
        uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return False
    return True


@login_required
def content_library(request, workspace_id):
    from apps.brands.models import BrandProfile
    from apps.composer.models import Post

    posts = Post.objects.filter(workspace=request.workspace).select_related(
        "brand", "campaign", "generated_source"
    ).prefetch_related(
        "media_attachments__media_asset", "platform_posts__social_account"
    )
    generated = GeneratedContent.objects.filter(workspace=request.workspace).select_related(
        "brand", "campaign", "composer_post", "request"
    ).prefetch_related("visual_briefs__media_asset")
    posts, generated = _library_filters(request, posts, generated)
    items = []
    for post in posts:
        media = next(iter(post.media_attachments.all()), None)
        items.append({"kind": "post", "object": post, "created_at": post.created_at, "title": post.title,
                      "body": post.caption, "origin": post.get_origin_display(), "media": media.media_asset if media else None,
                      "tags": post.tags or [], "source": getattr(post, "generated_source", None)})
    for output in generated:
        visual = next((brief for brief in output.visual_briefs.all() if brief.media_asset_id), None)
        items.append({"kind": "generated", "object": output, "created_at": output.created_at, "title": output.title,
                      "body": output.body, "origin": "AI generated", "media": visual.media_asset if visual else None,
                      "tags": (output.metadata or {}).get("tags", []), "source": output})
    query = request.GET.get("q", "").strip().casefold()
    if query:
        items = [item for item in items if query in " ".join([
            item["title"] or "", item["body"] or "", *[str(tag) for tag in item["tags"]]
        ]).casefold()]
    items.sort(key=lambda item: item["created_at"], reverse=True)
    page = Paginator(items, 24).get_page(request.GET.get("page"))
    return render(request, "content_intelligence/library.html", {
        "workspace": request.workspace, "page": page,
        "brands": BrandProfile.objects.filter(workspace=request.workspace),
        "campaigns": Campaign.objects.filter(workspace=request.workspace),
        "filters": request.GET, "settings_active": "content_library",
    })


@login_required
@require_POST
def content_library_action(request, workspace_id):
    from apps.composer.models import Post
    from apps.composer.services import clone_post

    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    kind, object_id, action = request.POST.get("kind"), request.POST.get("id"), request.POST.get("action")
    if kind == "post":
        try:
            item = Post.objects.get(id=object_id, workspace=request.workspace)
        except (Post.DoesNotExist, ValueError):
            raise Http404 from None
        if action == "duplicate":
            copy = clone_post(item, author=request.user)
            return redirect("composer:compose_edit", workspace_id=request.workspace.id, post_id=copy.id)
    elif kind == "generated":
        try:
            item = GeneratedContent.objects.select_related("request", "brand").get(id=object_id, workspace=request.workspace)
        except (GeneratedContent.DoesNotExist, ValueError):
            raise Http404 from None
        if action == "reuse":
            post, _ = create_composer_draft_service(output=item, user=request.user)
            return redirect("composer:compose_edit", workspace_id=request.workspace.id, post_id=post.id)
        if action == "regenerate":
            old = item.request
            context = old.context or {}
            queued = queue_generation(brand=item.brand, provider=old.provider, platform=old.platform,
                                      content_type=old.content_type, user=request.user, model=old.model,
                                      audience=old.audience, instruction=context.get("instruction", ""))
            return redirect("content_intelligence:generation_request_detail", workspace_id=request.workspace.id,
                            brand_id=item.brand_id, request_id=queued.id)
    else:
        raise Http404
    if action == "archive":
        item.archived_at = timezone.now()
        if kind == "generated":
            item.status = GeneratedContent.Status.ARCHIVED
            item.save(update_fields=["archived_at", "status"])
        else:
            item.save(update_fields=["archived_at"])
    elif action == "restore":
        item.archived_at = None
        if kind == "generated":
            item.status = GeneratedContent.Status.DRAFT
            item.save(update_fields=["archived_at", "status"])
        else:
            item.save(update_fields=["archived_at"])
    return redirect("content_intelligence:content_library", workspace_id=request.workspace.id)


@login_required
@require_POST
def content_library_bulk(request, workspace_id):
    from apps.composer.models import Post

    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    post_ids, generated_ids = [], []
    for value in request.POST.getlist("selected"):
        kind, _, object_id = value.partition(":")
        if _is_uuid(object_id):
            (post_ids if kind == "post" else generated_ids if kind == "generated" else []).append(object_id)
    if request.POST.get("action") == "assign_campaign":
        try:
            campaign = Campaign.objects.get(id=request.POST.get("campaign"), workspace=request.workspace)
        except (Campaign.DoesNotExist, ValueError):
            raise Http404 from None
        Post.objects.filter(workspace=request.workspace, id__in=post_ids).update(campaign=campaign)
        GeneratedContent.objects.filter(workspace=request.workspace, id__in=generated_ids).update(campaign=campaign)
        messages.success(request, "Campaign assigned to selected items.")
    else:
        now = timezone.now()
        Post.objects.filter(workspace=request.workspace, id__in=post_ids).update(archived_at=now)
        GeneratedContent.objects.filter(workspace=request.workspace, id__in=generated_ids).update(
            archived_at=now, status=GeneratedContent.Status.ARCHIVED
        )
        messages.success(request, "Selected library items archived.")
    return redirect("content_intelligence:content_library", workspace_id=request.workspace.id)


@login_required
@require_http_methods(["GET", "POST"])
def campaign_create(request, workspace_id):
    if not request.workspace_membership.effective_permissions.get("create_posts", False):
        raise PermissionDenied("Permission denied: create_posts")
    form = CampaignForm(request.POST or None, workspace=request.workspace)
    if request.method == "POST" and form.is_valid():
        campaign = form.save(commit=False)
        campaign.workspace = request.workspace
        campaign.save()
        messages.success(request, "Campaign created.")
        return redirect("content_intelligence:content_library", workspace_id=request.workspace.id)
    return render(request, "content_intelligence/campaign_form.html", {"workspace": request.workspace, "form": form, "settings_active": "brands"})
