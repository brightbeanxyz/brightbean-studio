from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import BrandProfileForm
from .models import BrandProfile


def _can_manage(request):
    return bool(request.workspace_membership.effective_permissions.get("manage_brand", False))


def _get_brand(request, brand_id):
    try:
        return BrandProfile.objects.get(id=brand_id, workspace=request.workspace)
    except BrandProfile.DoesNotExist:
        raise Http404 from None


@login_required
def brand_list(request, workspace_id):
    brands = BrandProfile.objects.for_workspace(request.workspace.id)
    return render(
        request,
        "brands/list.html",
        {
            "workspace": request.workspace,
            "brands": brands,
            "can_manage_brands": _can_manage(request),
            "settings_active": "brands",
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def brand_create(request, workspace_id):
    if not _can_manage(request):
        raise PermissionDenied("Permission denied: manage_brand")
    form = BrandProfileForm(request.POST or None, workspace=request.workspace)
    if request.method == "POST" and form.is_valid():
        brand = form.save()
        messages.success(request, f'Brand "{brand.name}" created.')
        return redirect("brands:list", workspace_id=request.workspace.id)
    return render(
        request,
        "brands/form.html",
        {"workspace": request.workspace, "form": form, "brand": None, "settings_active": "brands"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def brand_edit(request, workspace_id, brand_id):
    if not _can_manage(request):
        raise PermissionDenied("Permission denied: manage_brand")
    brand = _get_brand(request, brand_id)
    form = BrandProfileForm(request.POST or None, instance=brand, workspace=request.workspace)
    if request.method == "POST" and form.is_valid():
        brand = form.save()
        messages.success(request, f'Brand "{brand.name}" updated.')
        return redirect("brands:list", workspace_id=request.workspace.id)
    return render(
        request,
        "brands/form.html",
        {"workspace": request.workspace, "form": form, "brand": brand, "settings_active": "brands"},
    )
