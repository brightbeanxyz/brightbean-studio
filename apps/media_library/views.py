"""Media library views - all function-based, matching existing project patterns."""

import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.common.validators import normalize_tags
from apps.members.decorators import require_org_role, require_permission

from .models import MediaAsset, MediaFolder
from .services import (
    ProtectedAssetError,
    create_asset,
    create_folder,
    create_version,
    delete_asset,
    restore_version,
)
from .tasks import process_image_edit, process_media_asset, process_video_trim
from .validators import get_accepted_file_types


def _get_workspace_or_404(request, workspace_id):
    """Get workspace and verify the user has access via the RBAC middleware."""
    if not request.workspace or str(request.workspace.id) != str(workspace_id):
        raise Http404
    return request.workspace


# ──────────────────────────────────────────────────────────────
#  Library Index
# ──────────────────────────────────────────────────────────────


@login_required
def library_index(request, workspace_id):
    workspace = _get_workspace_or_404(request, workspace_id)

    # Base queryset: workspace assets + shared org assets
    qs = MediaAsset.objects.for_workspace_with_shared(
        workspace_id=workspace.id,
        organization_id=workspace.organization_id,
    ).select_related("uploaded_by", "folder")

    # Filters
    file_type = request.GET.get("type")
    if file_type and file_type in dict(MediaAsset.MediaType.choices):
        qs = qs.filter(media_type=file_type)

    folder_id = request.GET.get("folder")
    if folder_id:
        qs = qs.filter(folder_id=folder_id)
    elif request.GET.get("folder") is None and not request.GET.get("q"):
        pass  # Show all

    starred = request.GET.get("starred")
    if starred == "1":
        qs = qs.filter(is_starred=True)

    uploader = request.GET.get("uploader")
    if uploader:
        qs = qs.filter(uploaded_by_id=uploader)

    # Search
    query = request.GET.get("q", "").strip()
    if query:
        qs = MediaAsset.objects.search(query, queryset=qs)

    # Sort
    sort = request.GET.get("sort", "-created_at")
    sort_options = {
        "name": "filename",
        "-name": "-filename",
        "date": "created_at",
        "-date": "-created_at",
        "size": "file_size",
        "-size": "-file_size",
    }
    qs = qs.order_by(sort_options.get(sort, "-created_at"))

    # Pagination
    paginator = Paginator(qs, 48)
    page = paginator.get_page(request.GET.get("page", 1))

    # Folders for sidebar
    folders = MediaFolder.objects.filter(
        workspace=workspace,
        parent_folder__isnull=True,
    ).prefetch_related("subfolders__subfolders")

    # HTMX partial response
    if request.htmx:
        return render(
            request,
            "media_library/_asset_grid.html",
            {
                "page": page,
                "workspace": workspace,
                "query": query,
                "current_sort": sort,
            },
        )

    context = {
        "workspace": workspace,
        "page": page,
        "folders": folders,
        "query": query,
        "current_folder": folder_id,
        "current_type": file_type,
        "current_sort": sort,
        "is_starred": starred == "1",
        "file_types": MediaAsset.MediaType.choices,
        "accepted_file_types": get_accepted_file_types(),
        "max_bulk_upload": getattr(settings, "MEDIA_LIBRARY_MAX_BULK_UPLOAD", 50),
        "settings_active": "media",
    }
    return render(request, "media_library/library_index.html", context)


# ──────────────────────────────────────────────────────────────
#  Upload
# ──────────────────────────────────────────────────────────────


@login_required
@require_permission("upload_media")
@require_POST
def upload(request, workspace_id):
    workspace = _get_workspace_or_404(request, workspace_id)

    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"error": "No files provided"}, status=400)

    max_bulk = getattr(settings, "MEDIA_LIBRARY_MAX_BULK_UPLOAD", 50)
    if len(files) > max_bulk:
        return JsonResponse({"error": f"Maximum {max_bulk} files per upload"}, status=400)

    folder_id = request.POST.get("folder_id")
    folder = None
    if folder_id:
        folder = get_object_or_404(MediaFolder, pk=folder_id, workspace=workspace)

    results = []
    for uploaded_file in files:
        try:
            asset = create_asset(
                organization=workspace.organization,
                workspace=workspace,
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
                folder=folder,
            )
            # Enqueue background processing
            process_media_asset(str(asset.id))
            results.append({"id": str(asset.id), "status": "ok"})
        except ValidationError as e:
            results.append(
                {
                    "filename": uploaded_file.name,
                    "status": "error",
                    "errors": e.messages if hasattr(e, "messages") else [str(e)],
                }
            )

    # If HTMX request, return the new asset cards
    if request.htmx:
        assets = MediaAsset.objects.filter(id__in=[r["id"] for r in results if r["status"] == "ok"])
        return render(
            request,
            "media_library/_asset_grid_items.html",
            {
                "assets": assets,
                "workspace": workspace,
            },
        )

    return JsonResponse({"results": results})


# ──────────────────────────────────────────────────────────────
#  Search
# ──────────────────────────────────────────────────────────────


@login_required
@require_GET
def search(request, workspace_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    query = request.GET.get("q", "").strip()

    qs = MediaAsset.objects.for_workspace_with_shared(
        workspace_id=workspace.id,
        organization_id=workspace.organization_id,
    )
    if query:
        qs = MediaAsset.objects.search(query, queryset=qs)

    paginator = Paginator(qs, 48)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "media_library/_asset_grid.html",
        {
            "page": page,
            "workspace": workspace,
            "query": query,
        },
    )


# ──────────────────────────────────────────────────────────────
#  Asset Detail
# ──────────────────────────────────────────────────────────────


@login_required
def asset_detail(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace_with_shared(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
        ),
        pk=asset_id,
    )

    versions = asset.versions.all()[:10]

    context = {
        "asset": asset,
        "workspace": workspace,
        "versions": versions,
    }

    if request.htmx:
        return render(request, "media_library/_asset_detail_panel.html", context)
    return render(request, "media_library/asset_detail.html", context)


# ──────────────────────────────────────────────────────────────
#  Asset Edit (image crop/rotate/flip, video trim)
# ──────────────────────────────────────────────────────────────


@login_required
@require_permission("edit_media")
@require_http_methods(["GET", "POST"])
def asset_edit(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace(workspace.id),
        pk=asset_id,
    )

    # Shared assets are read-only
    if asset.is_shared:
        raise Http404

    if request.method == "POST":
        if asset.media_type in (MediaAsset.MediaType.IMAGE, MediaAsset.MediaType.GIF):
            operations = {}
            # Parse and validate crop data
            if request.POST.get("crop_x") is not None and request.POST.get("crop_x") != "":
                try:
                    crop_x = int(request.POST["crop_x"])
                    crop_y = int(request.POST["crop_y"])
                    crop_w = int(request.POST["crop_width"])
                    crop_h = int(request.POST["crop_height"])
                    if crop_x < 0 or crop_y < 0 or crop_w <= 0 or crop_h <= 0:
                        raise ValueError("Crop dimensions must be positive")
                    operations["crop"] = {
                        "x": crop_x,
                        "y": crop_y,
                        "width": crop_w,
                        "height": crop_h,
                    }
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid crop parameters"}, status=400)
            if request.POST.get("rotate"):
                try:
                    rotate_val = int(request.POST["rotate"])
                    if rotate_val not in (0, 90, 180, 270):
                        raise ValueError("Rotate must be 0, 90, 180, or 270")
                    operations["rotate"] = rotate_val
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid rotate parameter"}, status=400)
            if request.POST.get("flip"):
                flip_val = request.POST["flip"]
                if flip_val not in ("horizontal", "vertical"):
                    return JsonResponse({"error": "Invalid flip parameter"}, status=400)
                operations["flip"] = flip_val
            if request.POST.get("resize_width") and request.POST.get("resize_height"):
                try:
                    rw = int(request.POST["resize_width"])
                    rh = int(request.POST["resize_height"])
                    if rw <= 0 or rh <= 0 or rw > 10000 or rh > 10000:
                        raise ValueError("Resize dimensions out of range")
                    operations["resize"] = {"width": rw, "height": rh}
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid resize parameters"}, status=400)

            if operations:
                # Build change description
                parts = []
                if "crop" in operations:
                    parts.append(f"Cropped to {operations['crop']['width']}x{operations['crop']['height']}")
                if "rotate" in operations:
                    parts.append(f"Rotated {operations['rotate']}deg")
                if "flip" in operations:
                    parts.append(f"Flipped {operations['flip']}")
                if "resize" in operations:
                    parts.append(f"Resized to {operations['resize']['width']}x{operations['resize']['height']}")
                description = ", ".join(parts)

                version = create_version(
                    asset=asset,
                    file=asset.file,
                    change_description=description,
                    created_by=request.user,
                )
                process_image_edit(str(version.id), operations)

        elif asset.media_type == MediaAsset.MediaType.VIDEO:
            start = request.POST.get("trim_start")
            end = request.POST.get("trim_end")
            if start is not None and end is not None:
                start_seconds = float(start)
                end_seconds = float(end)
                description = f"Trimmed to {start_seconds:.1f}s - {end_seconds:.1f}s"

                version = create_version(
                    asset=asset,
                    file=asset.file,
                    change_description=description,
                    created_by=request.user,
                )
                process_video_trim(str(version.id), start_seconds, end_seconds)

        return redirect("media_library:asset_detail", workspace_id=workspace.id, asset_id=asset.id)

    context = {
        "asset": asset,
        "workspace": workspace,
    }
    return render(request, "media_library/asset_edit.html", context)


# ──────────────────────────────────────────────────────────────
#  Asset Actions
# ──────────────────────────────────────────────────────────────


@login_required
@require_permission("upload_media")
@require_POST
def asset_star_toggle(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace_with_shared(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
        ),
        pk=asset_id,
    )
    asset.is_starred = not asset.is_starred
    asset.save(update_fields=["is_starred"])

    if request.htmx:
        return render(
            request,
            "media_library/_star_button.html",
            {
                "asset": asset,
                "workspace": workspace,
            },
        )
    return JsonResponse({"is_starred": asset.is_starred})


@login_required
@require_permission("edit_media")
@require_POST
def asset_update_tags(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace(workspace.id),
        pk=asset_id,
    )

    try:
        body = json.loads(request.body) if request.content_type == "application/json" else request.POST.getlist("tags")
        asset.tags = normalize_tags(body)
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    asset.save(update_fields=["tags", "updated_at"])

    if request.htmx:
        return render(
            request,
            "media_library/_tag_list.html",
            {
                "asset": asset,
                "workspace": workspace,
            },
        )
    return JsonResponse({"tags": asset.tags})


@login_required
@require_permission("edit_media")
@require_POST
def asset_move(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace(workspace.id),
        pk=asset_id,
    )

    folder_id = request.POST.get("folder_id")
    if folder_id:
        folder = get_object_or_404(MediaFolder, pk=folder_id, workspace=workspace)
        asset.folder = folder
    else:
        asset.folder = None  # Move to root
    asset.save(update_fields=["folder", "updated_at"])

    if request.htmx:
        return render(
            request,
            "media_library/_asset_card.html",
            {
                "asset": asset,
                "workspace": workspace,
            },
        )
    return JsonResponse({"status": "ok"})


@login_required
@require_permission("delete_media")
@require_POST
def asset_delete(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace(workspace.id),
        pk=asset_id,
    )

    # Shared assets cannot be deleted from workspace context
    if asset.is_shared:
        return JsonResponse({"error": "Cannot delete shared assets from workspace context"}, status=403)

    try:
        delete_asset(asset)
    except ProtectedAssetError as e:
        if request.htmx:
            return render(
                request,
                "media_library/_delete_blocked.html",
                {
                    "asset": asset,
                    "referencing_posts": e.referencing_posts,
                    "workspace": workspace,
                },
            )
        return JsonResponse(
            {
                "error": "Asset is referenced by scheduled posts",
                "posts": e.referencing_posts,
            },
            status=409,
        )

    if request.htmx:
        from django.http import HttpResponse

        response = HttpResponse(status=200)
        response["HX-Trigger"] = "assetDeleted"
        return response
    return JsonResponse({"status": "deleted"})


@login_required
@require_GET
def asset_download(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace_with_shared(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
        ),
        pk=asset_id,
    )

    storage_backend = getattr(settings, "STORAGE_BACKEND", "local")
    if storage_backend == "s3":
        # For S3, redirect to a signed URL
        return redirect(asset.file.url)

    # For local storage, serve the file
    return FileResponse(
        asset.file.open("rb"),
        as_attachment=True,
        filename=asset.original_filename,
    )


# ──────────────────────────────────────────────────────────────
#  Folders
# ──────────────────────────────────────────────────────────────


@login_required
@require_permission("manage_media")
@require_POST
def folder_create(request, workspace_id):
    workspace = _get_workspace_or_404(request, workspace_id)

    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Folder name is required"}, status=400)

    parent_id = request.POST.get("parent_folder_id")
    parent = None
    if parent_id:
        parent = get_object_or_404(MediaFolder, pk=parent_id, workspace=workspace)

    try:
        folder = create_folder(
            organization=workspace.organization,
            workspace=workspace,
            name=name,
            parent_folder=parent,
        )
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)

    if request.htmx:
        folders = MediaFolder.objects.filter(
            workspace=workspace,
            parent_folder__isnull=True,
        ).prefetch_related("subfolders__subfolders")
        return render(
            request,
            "media_library/_folder_tree.html",
            {
                "folders": folders,
                "workspace": workspace,
            },
        )
    return JsonResponse({"id": str(folder.id), "name": folder.name})


@login_required
@require_permission("manage_media")
@require_POST
def folder_rename(request, workspace_id, folder_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    folder = get_object_or_404(MediaFolder, pk=folder_id, workspace=workspace)

    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "Folder name is required"}, status=400)

    # Check for duplicate sibling name before saving
    duplicate = (
        MediaFolder.objects.filter(
            workspace=workspace,
            parent_folder=folder.parent_folder,
            name=name,
        )
        .exclude(pk=folder.pk)
        .exists()
    )
    if duplicate:
        return JsonResponse(
            {"error": f"A folder named '{name}' already exists in this location."},
            status=400,
        )

    folder.name = name
    folder.save(update_fields=["name", "updated_at"])

    if request.htmx:
        folders = MediaFolder.objects.filter(
            workspace=workspace,
            parent_folder__isnull=True,
        ).prefetch_related("subfolders__subfolders")
        return render(
            request,
            "media_library/_folder_tree.html",
            {
                "folders": folders,
                "workspace": workspace,
            },
        )
    return JsonResponse({"id": str(folder.id), "name": folder.name})


@login_required
@require_permission("manage_media")
@require_POST
def folder_delete(request, workspace_id, folder_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    folder = get_object_or_404(MediaFolder, pk=folder_id, workspace=workspace)

    # Move assets to parent folder (or root)
    MediaAsset.objects.filter(folder=folder).update(folder=folder.parent_folder)

    # Move subfolders to parent
    MediaFolder.objects.filter(parent_folder=folder).update(parent_folder=folder.parent_folder)

    folder.delete()

    if request.htmx:
        folders = MediaFolder.objects.filter(
            workspace=workspace,
            parent_folder__isnull=True,
        ).prefetch_related("subfolders__subfolders")
        return render(
            request,
            "media_library/_folder_tree.html",
            {
                "folders": folders,
                "workspace": workspace,
            },
        )
    return JsonResponse({"status": "deleted"})


# ──────────────────────────────────────────────────────────────
#  Tags
# ──────────────────────────────────────────────────────────────


@login_required
@require_GET
def tag_autocomplete(request, workspace_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    query = request.GET.get("q", "").strip().lower()

    if not query or len(query) < 1:
        return JsonResponse([], safe=False)

    # Collect distinct tags from workspace assets
    assets = (
        MediaAsset.objects.for_workspace_with_shared(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
        )
        .exclude(tags=[])
        .values_list("tags", flat=True)
    )

    all_tags = set()
    for tag_list in assets[:500]:
        for tag in tag_list:
            if query in tag.lower():
                all_tags.add(tag)

    return JsonResponse(sorted(all_tags)[:20], safe=False)


# ──────────────────────────────────────────────────────────────
#  Versions
# ──────────────────────────────────────────────────────────────


@login_required
@require_GET
def version_list(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace_with_shared(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
        ),
        pk=asset_id,
    )

    versions = asset.versions.all()

    return render(
        request,
        "media_library/_version_list.html",
        {
            "asset": asset,
            "versions": versions,
            "workspace": workspace,
        },
    )


@login_required
@require_permission("edit_media")
@require_POST
def version_restore(request, workspace_id, asset_id, version_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace(workspace.id),
        pk=asset_id,
    )
    version = get_object_or_404(asset.versions, pk=version_id)

    restore_version(asset, version, request.user)

    if request.htmx:
        versions = asset.versions.all()
        return render(
            request,
            "media_library/_version_list.html",
            {
                "asset": asset,
                "versions": versions,
                "workspace": workspace,
            },
        )
    return redirect("media_library:asset_detail", workspace_id=workspace.id, asset_id=asset.id)


# ──────────────────────────────────────────────────────────────
#  Processing Status (polled by HTMX)
# ──────────────────────────────────────────────────────────────


@login_required
@require_GET
def processing_status(request, workspace_id, asset_id):
    workspace = _get_workspace_or_404(request, workspace_id)
    asset = get_object_or_404(
        MediaAsset.objects.for_workspace_with_shared(
            workspace_id=workspace.id,
            organization_id=workspace.organization_id,
        ),
        pk=asset_id,
    )

    if request.htmx and asset.processing_status == MediaAsset.ProcessingStatus.COMPLETED:
        # Return the completed asset card to replace the placeholder
        return render(
            request,
            "media_library/_asset_card.html",
            {
                "asset": asset,
                "workspace": workspace,
            },
        )

    return JsonResponse(
        {
            "status": asset.processing_status,
            "thumbnail_url": asset.thumbnail.url if asset.thumbnail else None,
        }
    )


# ──────────────────────────────────────────────────────────────
#  Shared Org Library
# ──────────────────────────────────────────────────────────────


@login_required
@require_org_role("member")
def shared_library_index(request):
    org = request.org
    if not org:
        raise Http404

    qs = MediaAsset.objects.shared_only(org.id)

    # Search
    query = request.GET.get("q", "").strip()
    if query:
        qs = MediaAsset.objects.search(query, queryset=qs)

    # Filter by type
    file_type = request.GET.get("type")
    if file_type and file_type in dict(MediaAsset.MediaType.choices):
        qs = qs.filter(media_type=file_type)

    sort = request.GET.get("sort", "-created_at")
    sort_options = {
        "name": "filename",
        "-name": "-filename",
        "date": "created_at",
        "-date": "-created_at",
        "size": "file_size",
        "-size": "-file_size",
    }
    qs = qs.order_by(sort_options.get(sort, "-created_at"))

    paginator = Paginator(qs, 48)
    page = paginator.get_page(request.GET.get("page", 1))

    is_admin = request.org_membership and request.org_membership.org_role in ("owner", "admin")

    if request.htmx:
        return render(
            request,
            "media_library/_shared_asset_grid.html",
            {
                "page": page,
                "query": query,
                "is_admin": is_admin,
            },
        )

    return render(
        request,
        "media_library/shared_library.html",
        {
            "page": page,
            "query": query,
            "current_type": file_type,
            "current_sort": sort,
            "is_admin": is_admin,
            "file_types": MediaAsset.MediaType.choices,
            "accepted_file_types": get_accepted_file_types(),
            "settings_active": "media",
        },
    )


@login_required
@require_org_role("admin")
@require_POST
def shared_upload(request):
    org = request.org
    if not org:
        raise Http404

    files = request.FILES.getlist("files")
    if not files:
        return JsonResponse({"error": "No files provided"}, status=400)

    max_bulk = getattr(settings, "MEDIA_LIBRARY_MAX_BULK_UPLOAD", 50)
    if len(files) > max_bulk:
        return JsonResponse({"error": f"Maximum {max_bulk} files per upload"}, status=400)

    results = []
    for uploaded_file in files:
        try:
            asset = create_asset(
                organization=org,
                workspace=None,  # Shared = no workspace
                uploaded_file=uploaded_file,
                uploaded_by=request.user,
            )
            process_media_asset(str(asset.id))
            results.append({"id": str(asset.id), "status": "ok"})
        except ValidationError as e:
            results.append(
                {
                    "filename": uploaded_file.name,
                    "status": "error",
                    "errors": e.messages if hasattr(e, "messages") else [str(e)],
                }
            )

    if request.htmx:
        assets = MediaAsset.objects.filter(id__in=[r["id"] for r in results if r["status"] == "ok"])
        return render(
            request,
            "media_library/_shared_asset_grid_items.html",
            {
                "assets": assets,
                "is_admin": True,
            },
        )

    return JsonResponse({"results": results})


@login_required
@require_org_role("member")
def shared_asset_detail(request, asset_id):
    org = request.org
    if not org:
        raise Http404

    asset = get_object_or_404(
        MediaAsset.objects.shared_only(org.id),
        pk=asset_id,
    )

    versions = asset.versions.all()[:10]
    is_admin = request.org_membership and request.org_membership.org_role in ("owner", "admin")

    # Shared assets have no workspace. Templates branch on `is_shared_library`
    # to resolve org-scoped URLs (download, edit, delete, tags, versions).
    context = {
        "asset": asset,
        "workspace": None,
        "versions": versions,
        "is_shared_library": True,
        "is_admin": is_admin,
    }

    if request.htmx:
        return render(request, "media_library/_asset_detail_panel.html", context)
    return render(request, "media_library/asset_detail.html", context)


# ──────────────────────────────────────────────────────────────
#  Shared Org Library - Admin Mutations & Supporting Endpoints
# ──────────────────────────────────────────────────────────────


@login_required
@require_org_role("admin")
@require_http_methods(["GET", "POST"])
def shared_asset_edit(request, asset_id):
    org = request.org
    if not org:
        raise Http404
    asset = get_object_or_404(MediaAsset.objects.shared_only(org.id), pk=asset_id)

    if request.method == "POST":
        if asset.media_type in (MediaAsset.MediaType.IMAGE, MediaAsset.MediaType.GIF):
            operations = {}
            if request.POST.get("crop_x") is not None and request.POST.get("crop_x") != "":
                try:
                    crop_x = int(request.POST["crop_x"])
                    crop_y = int(request.POST["crop_y"])
                    crop_w = int(request.POST["crop_width"])
                    crop_h = int(request.POST["crop_height"])
                    if crop_x < 0 or crop_y < 0 or crop_w <= 0 or crop_h <= 0:
                        raise ValueError("Crop dimensions must be positive")
                    operations["crop"] = {
                        "x": crop_x,
                        "y": crop_y,
                        "width": crop_w,
                        "height": crop_h,
                    }
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid crop parameters"}, status=400)
            if request.POST.get("rotate"):
                try:
                    rotate_val = int(request.POST["rotate"])
                    if rotate_val not in (0, 90, 180, 270):
                        raise ValueError("Rotate must be 0, 90, 180, or 270")
                    operations["rotate"] = rotate_val
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid rotate parameter"}, status=400)
            if request.POST.get("flip"):
                flip_val = request.POST["flip"]
                if flip_val not in ("horizontal", "vertical"):
                    return JsonResponse({"error": "Invalid flip parameter"}, status=400)
                operations["flip"] = flip_val
            if request.POST.get("resize_width") and request.POST.get("resize_height"):
                try:
                    rw = int(request.POST["resize_width"])
                    rh = int(request.POST["resize_height"])
                    if rw <= 0 or rh <= 0 or rw > 10000 or rh > 10000:
                        raise ValueError("Resize dimensions out of range")
                    operations["resize"] = {"width": rw, "height": rh}
                except (ValueError, TypeError):
                    return JsonResponse({"error": "Invalid resize parameters"}, status=400)

            if operations:
                parts = []
                if "crop" in operations:
                    parts.append(f"Cropped to {operations['crop']['width']}x{operations['crop']['height']}")
                if "rotate" in operations:
                    parts.append(f"Rotated {operations['rotate']}deg")
                if "flip" in operations:
                    parts.append(f"Flipped {operations['flip']}")
                if "resize" in operations:
                    parts.append(f"Resized to {operations['resize']['width']}x{operations['resize']['height']}")
                description = ", ".join(parts)

                version = create_version(
                    asset=asset,
                    file=asset.file,
                    change_description=description,
                    created_by=request.user,
                )
                process_image_edit(str(version.id), operations)

        elif asset.media_type == MediaAsset.MediaType.VIDEO:
            start = request.POST.get("trim_start")
            end = request.POST.get("trim_end")
            if start is not None and end is not None:
                start_seconds = float(start)
                end_seconds = float(end)
                description = f"Trimmed to {start_seconds:.1f}s - {end_seconds:.1f}s"

                version = create_version(
                    asset=asset,
                    file=asset.file,
                    change_description=description,
                    created_by=request.user,
                )
                process_video_trim(str(version.id), start_seconds, end_seconds)

        return redirect("media_library_org:shared_asset_detail", asset_id=asset.id)

    context = {
        "asset": asset,
        "workspace": None,
        "is_shared_library": True,
        "is_admin": True,
    }
    return render(request, "media_library/asset_edit.html", context)


@login_required
@require_org_role("admin")
@require_POST
def shared_asset_delete(request, asset_id):
    org = request.org
    if not org:
        raise Http404
    asset = get_object_or_404(MediaAsset.objects.shared_only(org.id), pk=asset_id)

    try:
        delete_asset(asset)
    except ProtectedAssetError as e:
        if request.htmx:
            return render(
                request,
                "media_library/_delete_blocked.html",
                {
                    "asset": asset,
                    "referencing_posts": e.referencing_posts,
                    "is_shared_library": True,
                },
            )
        return JsonResponse(
            {"error": "Asset is referenced by scheduled posts", "posts": e.referencing_posts},
            status=409,
        )

    if request.htmx:
        from django.http import HttpResponse

        response = HttpResponse(status=200)
        response["HX-Trigger"] = "assetDeleted"
        return response
    return JsonResponse({"status": "deleted"})


@login_required
@require_org_role("admin")
@require_POST
def shared_asset_update_tags(request, asset_id):
    org = request.org
    if not org:
        raise Http404
    asset = get_object_or_404(MediaAsset.objects.shared_only(org.id), pk=asset_id)

    try:
        body = json.loads(request.body) if request.content_type == "application/json" else request.POST.getlist("tags")
        asset.tags = normalize_tags(body)
    except (json.JSONDecodeError, ValueError) as e:
        return JsonResponse({"error": str(e)}, status=400)
    asset.save(update_fields=["tags", "updated_at"])

    if request.htmx:
        return render(
            request,
            "media_library/_tag_list.html",
            {
                "asset": asset,
                "workspace": None,
                "is_shared_library": True,
                "is_admin": True,
            },
        )
    return JsonResponse({"tags": asset.tags})


@login_required
@require_org_role("member")
@require_GET
def shared_asset_download(request, asset_id):
    org = request.org
    if not org:
        raise Http404
    asset = get_object_or_404(MediaAsset.objects.shared_only(org.id), pk=asset_id)

    storage_backend = getattr(settings, "STORAGE_BACKEND", "local")
    if storage_backend == "s3":
        return redirect(asset.file.url)
    return FileResponse(
        asset.file.open("rb"),
        as_attachment=True,
        filename=asset.original_filename,
    )


@login_required
@require_org_role("member")
@require_GET
def shared_version_list(request, asset_id):
    org = request.org
    if not org:
        raise Http404
    asset = get_object_or_404(MediaAsset.objects.shared_only(org.id), pk=asset_id)

    versions = asset.versions.all()
    is_admin = request.org_membership and request.org_membership.org_role in ("owner", "admin")

    return render(
        request,
        "media_library/_version_list.html",
        {
            "asset": asset,
            "versions": versions,
            "workspace": None,
            "is_shared_library": True,
            "is_admin": is_admin,
        },
    )


@login_required
@require_org_role("member")
@require_GET
def shared_tag_autocomplete(request):
    org = request.org
    if not org:
        raise Http404
    query = request.GET.get("q", "").strip().lower()
    if not query or len(query) < 1:
        return JsonResponse([], safe=False)

    assets = MediaAsset.objects.shared_only(org.id).exclude(tags=[]).values_list("tags", flat=True)
    all_tags = set()
    for tag_list in assets[:500]:
        for tag in tag_list:
            if query in tag.lower():
                all_tags.add(tag)
    return JsonResponse(sorted(all_tags)[:20], safe=False)
