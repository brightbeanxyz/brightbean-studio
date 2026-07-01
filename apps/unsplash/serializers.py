"""DRF serializers for Unsplash integration and media folders.

Part of the brightbean-unsplash plugin.
"""

from __future__ import annotations

from rest_framework import serializers


class UnsplashPhotoResultSerializer(serializers.Serializer):
    """Individual photo result from Unsplash search."""

    id = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    width = serializers.IntegerField()
    height = serializers.IntegerField()
    color = serializers.CharField(allow_blank=True)
    urls = serializers.DictField()
    photographer = serializers.CharField()
    photographer_url = serializers.CharField()


class UnsplashSearchResponseSerializer(serializers.Serializer):
    """Full search response with pagination."""

    results = UnsplashPhotoResultSerializer(many=True)
    total = serializers.IntegerField()
    total_pages = serializers.IntegerField()
    page = serializers.IntegerField()


class UnsplashImportRequestSerializer(serializers.Serializer):
    """Request body for importing a photo from Unsplash."""

    photo_id = serializers.CharField(required=True)
    workspace_id = serializers.UUIDField(required=True)
    folder_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    alt_text = serializers.CharField(required=False, allow_blank=True, default="")
    force = serializers.BooleanField(required=False, default=False)


class MediaAssetImportResponseSerializer(serializers.ModelSerializer):
    """Response after importing a photo as a MediaAsset."""

    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        from apps.media_library.models import MediaAsset

        model = MediaAsset
        fields = [
            "id",
            "filename",
            "source",
            "source_url",
            "attribution",
            "width",
            "height",
            "file_size",
            "url",
            "thumbnail_url",
        ]

    def get_url(self, obj):
        if obj.file:
            return obj.file.url
        return ""

    def get_thumbnail_url(self, obj):
        if obj.thumbnail:
            return obj.thumbnail.url
        return ""


# ---------------------------------------------------------------------------
# Folder serializers
# ---------------------------------------------------------------------------


class MediaFolderSerializer(serializers.Serializer):
    """Read/write serializer for MediaFolder."""

    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    workspace_id = serializers.UUIDField(write_only=True, required=False)
    parent_folder_id = serializers.UUIDField(required=False, allow_null=True, default=None)
    parent_folder = serializers.UUIDField(source="parent_folder_id", read_only=True)
    depth = serializers.IntegerField(read_only=True)
    asset_count = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_asset_count(self, obj):
        return getattr(obj, "asset_count", obj.assets.count())

    def create(self, validated_data):
        from apps.media_library.models import MediaFolder
        from apps.workspaces.models import Workspace

        workspace_id = validated_data.pop("workspace_id", None)
        parent_folder_id = validated_data.pop("parent_folder_id", None)

        workspace = Workspace.objects.get(id=workspace_id)
        parent_folder = None
        if parent_folder_id:
            parent_folder = MediaFolder.objects.get(id=parent_folder_id)

        folder = MediaFolder(
            workspace=workspace,
            organization=workspace.organization,
            parent_folder=parent_folder,
            **validated_data,
        )
        folder.clean()
        folder.save()
        return folder

    def update(self, instance, validated_data):
        parent_folder_id = validated_data.pop("parent_folder_id", None)
        if parent_folder_id is not None:
            from apps.media_library.models import MediaFolder

            instance.parent_folder = MediaFolder.objects.get(id=parent_folder_id)

        for attr, value in validated_data.items():
            if attr != "workspace_id":
                setattr(instance, attr, value)

        instance.clean()
        instance.save()
        return instance
