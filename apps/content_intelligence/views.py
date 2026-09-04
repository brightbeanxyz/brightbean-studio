from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.brands.forms import EditorialStrategyForm
from apps.brands.models import BrandProfile, EditorialStrategy
from apps.brands.services import save_editorial_strategy

from .forms import AIProviderConfigurationForm, ContentPlanForm, GenerationForm, VisualBriefForm
from .generation import configured_providers, queue_generation
from .generation import create_composer_draft as create_composer_draft_service
from .models import AIProviderConfiguration, ContentPlan, GeneratedContent, GenerationRequest, VisualBrief
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
