"""Unsplash and media-folder API views.

All endpoints require TokenAuthentication. The token is passed as:
    Authorization: Token <token>

Part of the brightbean-unsplash plugin — lives outside the main repo
so upstream merges can't destroy it.
"""

from __future__ import annotations

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.unsplash.serializers import (
    MediaAssetImportResponseSerializer,
    MediaFolderSerializer,
    UnsplashImportRequestSerializer,
    UnsplashSearchResponseSerializer,
)

# ---------------------------------------------------------------------------
# Unsplash endpoints
# ---------------------------------------------------------------------------


class UnsplashSearchView(APIView):
    """GET /api/v1/media/unsplash/search/ — search Unsplash for stock photos."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.unsplash.services.unsplash import UnsplashClient, UnsplashError

        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "Query parameter 'q' is required."}, status=400)

        page = int(request.query_params.get("page", 1))
        per_page = min(int(request.query_params.get("per_page", 20)), 30)
        orientation = request.query_params.get("orientation") or None
        color = request.query_params.get("color") or None

        # Validate orientation
        valid_orientations = {"landscape", "portrait", "squarish"}
        if orientation and orientation not in valid_orientations:
            return Response(
                {"error": f"Invalid orientation. Must be one of: {valid_orientations}"},
                status=400,
            )

        workspace_key = _resolve_workspace_unsplash_key(request)
        client = UnsplashClient(workspace_key=workspace_key)
        if not client.is_configured:
            return Response({"error": "Unsplash API key is not configured."}, status=503)

        try:
            results = client.search_photos(
                query,
                page=page,
                per_page=per_page,
                orientation=orientation,
                color=color,
            )
        except UnsplashError as exc:
            status = 500
            if "Rate limit" in str(exc) or "rate limited" in str(exc):
                status = 429
            elif "invalid" in str(exc).lower() or "not configured" in str(exc).lower():
                status = 401
            return Response({"error": str(exc)}, status=status)

        response_data = {
            "results": [
                {
                    "id": p.id,
                    "description": p.description or "",
                    "width": p.width,
                    "height": p.height,
                    "color": p.color or "",
                    "urls": p.urls,
                    "photographer": p.photographer,
                    "photographer_url": p.photographer_url,
                }
                for p in results.results
            ],
            "total": results.total,
            "total_pages": results.total_pages,
            "page": results.page,
        }
        serializer = UnsplashSearchResponseSerializer(data=response_data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data)


class UnsplashImportView(APIView):
    """POST /api/v1/media/unsplash/import/ — import a photo from Unsplash."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from django.core.files.base import ContentFile

        from apps.media_library.models import MediaAsset, MediaFolder
        from apps.unsplash.services.unsplash import (
            UnsplashClient,
            UnsplashError,
            UnsplashNotFound,
        )
        from apps.workspaces.models import Workspace

        # Validate input
        serializer = UnsplashImportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        photo_id = validated["photo_id"]
        workspace_id = validated["workspace_id"]
        folder_id = validated.get("folder_id")
        alt_text = validated.get("alt_text", "")
        force = validated.get("force", False)

        # Resolve workspace
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return Response({"error": "Workspace not found."}, status=404)

        # Check dedup
        existing = MediaAsset.objects.filter(workspace=workspace, external_id=photo_id).first()
        if existing and not force:
            return Response(
                {
                    "error": "Photo already imported.",
                    "asset_id": str(existing.id),
                    "detail": "Use force=true to re-import.",
                },
                status=409,
            )

        # Resolve folder if provided
        folder = None
        if folder_id:
            try:
                folder = MediaFolder.objects.get(id=folder_id, workspace=workspace)
            except MediaFolder.DoesNotExist:
                return Response({"error": "Folder not found."}, status=404)

        # Download from Unsplash
        # Use global UNSPLASH_ACCESS_KEY (workspace-specific key not available yet)
        from django.conf import settings

        workspace_key = getattr(settings, "UNSPLASH_ACCESS_KEY", "")
        client = UnsplashClient(workspace_key=workspace_key)
        if not client.is_configured:
            return Response({"error": "Unsplash API key is not configured."}, status=503)

        try:
            photo = client.get_photo(photo_id)
            # Trigger download event, then download the image bytes
            client._trigger_download_event(photo.download_url)
            import requests as _requests

            img_response = _requests.get(photo.urls["regular"], timeout=30)
            if not img_response.ok:
                return Response(
                    {"error": f"Failed to download image: {img_response.status_code}"},
                    status=500,
                )
            image_bytes = img_response.content
        except UnsplashNotFound:
            return Response({"error": f"Photo {photo_id} not found on Unsplash."}, status=404)
        except UnsplashError as exc:
            return Response({"error": f"Unsplash API error: {exc}"}, status=500)

        description = photo.description or ""
        attribution_text = f"Photo by {photo.photographer} on Unsplash"
        source_url = f"https://unsplash.com/photos/{photo_id}"
        filename = f"{photo_id}.jpg"

        # Create the asset
        asset = MediaAsset(
            workspace=workspace,
            organization=workspace.organization,
            uploaded_by=request.user,
            folder=folder,
            filename=filename,
            media_type=MediaAsset.MediaType.IMAGE,
            mime_type="image/jpeg",
            file_size=len(image_bytes),
            width=photo.width,
            height=photo.height,
            alt_text=alt_text or description,
            source="unsplash",
            source_url=source_url,
            attribution=attribution_text,
            external_id=photo_id,
        )
        asset.file.save(filename, ContentFile(image_bytes), save=False)
        asset.save()

        response_serializer = MediaAssetImportResponseSerializer(asset, context={"request": request})
        return Response(response_serializer.data, status=201)


# ---------------------------------------------------------------------------
# Folder CRUD endpoints
# ---------------------------------------------------------------------------


class FolderListCreateView(APIView):
    """GET/POST /api/v1/media/folders/ — list or create folders."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from django.db.models import Count

        from apps.media_library.models import MediaFolder

        workspace_id = request.query_params.get("workspace_id")
        if not workspace_id:
            return Response({"error": "workspace_id query param is required."}, status=400)

        folders = (
            MediaFolder.objects.filter(workspace_id=workspace_id).annotate(asset_count=Count("assets")).order_by("name")
        )

        data = [
            {
                "id": f.id,
                "name": f.name,
                "parent_folder": str(f.parent_folder_id) if f.parent_folder_id else None,
                "depth": f.depth,
                "asset_count": f.asset_count,
                "created_at": f.created_at,
            }
            for f in folders
        ]
        return Response({"results": data})

    def post(self, request):
        serializer = MediaFolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        folder = serializer.save()

        # Return the created folder
        return Response(
            {
                "id": folder.id,
                "name": folder.name,
                "parent_folder": str(folder.parent_folder_id) if folder.parent_folder_id else None,
                "depth": folder.depth,
                "asset_count": folder.assets.count(),
                "created_at": folder.created_at,
            },
            status=201,
        )


class FolderDetailView(APIView):
    """PATCH/DELETE /api/v1/media/folders/<uuid:id>/ — rename, move, or delete."""

    permission_classes = [permissions.IsAuthenticated]

    def _get_folder(self, id):
        from apps.media_library.models import MediaFolder

        try:
            return MediaFolder.objects.get(id=id)
        except MediaFolder.DoesNotExist:
            return None

    def patch(self, request, id):
        folder = self._get_folder(id)
        if not folder:
            return Response({"error": "Folder not found."}, status=404)

        serializer = MediaFolderSerializer(folder, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        folder = serializer.save()

        return Response(
            {
                "id": folder.id,
                "name": folder.name,
                "parent_folder": str(folder.parent_folder_id) if folder.parent_folder_id else None,
                "depth": folder.depth,
                "asset_count": folder.assets.count(),
                "created_at": folder.created_at,
            }
        )

    def delete(self, request, id):
        folder = self._get_folder(id)
        if not folder:
            return Response({"error": "Folder not found."}, status=404)

        asset_count = folder.assets.count()
        subfolder_count = folder.subfolders.count()
        if asset_count > 0 or subfolder_count > 0:
            n = asset_count + subfolder_count
            return Response(
                {"error": f"Folder is not empty. Move or delete {n} items first."},
                status=409,
            )

        folder.delete()
        return Response(status=204)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_workspace_unsplash_key(request) -> str | None:
    """Resolve the Unsplash API key for the user's first workspace.

    The search modal doesn't always know the workspace ID, so we check
    all of the user's workspace memberships and use the first non-empty
    unsplash_access_key we find. Falls back to the global UNSPLASH_ACCESS_KEY
    via the UnsplashClient constructor.
    """
    from apps.members.models import WorkspaceMembership

    workspace_ids = WorkspaceMembership.objects.filter(user=request.user).values_list("workspace_id", flat=True)

    if not workspace_ids:
        return None

    from apps.workspaces.models import Workspace

    for ws in Workspace.objects.filter(id__in=list(workspace_ids)):
        try:
            key = ws.integration_settings.get("unsplash_access_key", "")
            if key:
                return key
        except AttributeError:
            # integration_settings field doesn't exist yet
            pass

    # Return None to let UnsplashClient fall back to settings.UNSPLASH_ACCESS_KEY
    return None
