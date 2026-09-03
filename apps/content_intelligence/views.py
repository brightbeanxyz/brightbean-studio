from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.brands.forms import EditorialStrategyForm
from apps.brands.models import BrandProfile, EditorialStrategy
from apps.brands.services import save_editorial_strategy

from .forms import ContentPlanForm
from .models import ContentPlan
from .services import create_content_plan


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
