"""list_media, upload_media_from_url."""

from __future__ import annotations

import io
from typing import Any
from urllib.parse import urlparse

import httpx
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.media_library.models import MediaAsset
from apps.media_library.services import create_asset


def _serialize(asset: MediaAsset) -> dict[str, Any]:
    try:
        url = asset.file.url if asset.file else ""
    except Exception:
        url = ""
    return {
        "id": str(asset.id),
        "filename": asset.filename,
        "media_type": asset.media_type,
        "mime_type": asset.mime_type,
        "file_size": asset.file_size,
        "width": asset.width,
        "height": asset.height,
        "duration": asset.duration,
        "folder_id": str(asset.folder_id) if asset.folder_id else None,
        "is_starred": asset.is_starred,
        "url": url,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


def register(mcp, ctx):
    @mcp.tool()
    def list_media(
        folder_id: str | None = None,
        media_type: str | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List media assets in the current workspace (and shared org library).

        media_type: image | video | gif | document
        """
        ws = ctx.require_workspace()
        org_id = ws.organization_id
        qs = MediaAsset.objects.for_workspace_with_shared(ws.id, org_id).select_related("folder")
        if folder_id:
            qs = qs.filter(folder_id=folder_id)
        if media_type:
            qs = qs.filter(media_type=media_type)
        if search:
            qs = qs.filter(filename__icontains=search)
        qs = qs.order_by("-created_at")
        limit = max(1, min(int(limit), 200))
        offset = max(0, int(offset))
        total = qs.count()
        items = [_serialize(a) for a in qs[offset : offset + limit]]
        return {"total": total, "limit": limit, "offset": offset, "items": items}

    @mcp.tool()
    def upload_media_from_url(
        url: str,
        filename: str | None = None,
        folder_id: str | None = None,
    ) -> dict[str, Any]:
        """Download an image/video from ``url`` and add it to the workspace media library."""
        ctx.require_permission("upload_media")
        ws = ctx.require_workspace()

        if not filename:
            path = urlparse(url).path
            filename = path.rsplit("/", 1)[-1] or "download.bin"

        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content = resp.content

        upload = SimpleUploadedFile(filename, io.BytesIO(content).getvalue())

        folder = None
        if folder_id:
            from apps.media_library.models import MediaFolder

            folder = MediaFolder.objects.filter(id=folder_id, workspace_id=ws.id).first()

        asset = create_asset(
            organization=ws.organization,
            workspace=ws,
            uploaded_file=upload,
            uploaded_by=ctx.user,
            folder=folder,
        )
        return _serialize(asset)
