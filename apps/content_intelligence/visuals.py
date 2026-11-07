from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.composer.models import PostMedia
from apps.media_library.services import create_asset

from .image_providers import generate_image
from .models import AIProviderConfiguration, VisualBrief
from .providers import ProviderError

FORMAT_SIZES = {"square": "1024x1024", "portrait": "1024x1536", "landscape": "1536x1024"}


def build_visual_prompt(brief):
    brand = brief.brand
    content = brief.generated_content.body if brief.generated_content_id else ""
    return (
        f"Create a polished social media image for {brand.name}. Objective: {brief.objective}. "
        f"Style: {brief.style or 'aligned with the brand identity'}. Brand voice: {brand.brand_voice}. "
        f"Colors: {', '.join(brief.colors) or 'use the brand context'}. Format: {brief.format}. "
        f"Content context: {content[:1500] or 'none'}. Constraints: {brief.constraints or 'no extra constraints'}. "
        "Do not invent logos, testimonials, statistics, or claims. Do not include watermarks."
    )


def image_provider_configurations(organization):
    return [
        item
        for item in AIProviderConfiguration.objects.filter(
            organization=organization, provider__in=VisualBrief.Provider.values, is_enabled=True
        )
        if item.is_configured
    ]


def queue_visual_brief(*, brief):
    configuration = AIProviderConfiguration.objects.get(
        organization=brief.workspace.organization, provider=brief.provider, is_enabled=True
    )
    used = VisualBrief.objects.filter(
        workspace__organization=brief.workspace.organization,
        provider=brief.provider,
        created_at__date=timezone.localdate(),
    ).count()
    if used > configuration.daily_request_limit:
        raise ValueError("Daily image generation quota reached for this provider.")
    from .tasks import run_visual_generation

    run_visual_generation(str(brief.id))


def process_visual_brief(brief_id):
    brief = VisualBrief.objects.select_related(
        "brand", "workspace__organization", "requested_by", "generated_content", "post"
    ).get(id=brief_id)
    configuration = AIProviderConfiguration.objects.get(
        organization=brief.workspace.organization, provider=brief.provider, is_enabled=True
    )
    brief.status = VisualBrief.Status.PROCESSING
    brief.attempt_count += 1
    brief.prompt = build_visual_prompt(brief)
    brief.save(update_fields=["status", "attempt_count", "prompt"])
    try:
        image = generate_image(
            provider=brief.provider,
            model=brief.model or configuration.default_model,
            prompt=brief.prompt,
            size=FORMAT_SIZES[brief.format],
            api_key=configuration.api_key,
            timeout=configuration.timeout_seconds,
        )
        uploaded = ContentFile(image, name=f"ai-{brief.id}.png")
        with transaction.atomic():
            asset = create_asset(
                organization=brief.workspace.organization,
                workspace=brief.workspace,
                uploaded_file=uploaded,
                uploaded_by=brief.requested_by,
                alt_text=f"AI-generated visual for {brief.brand.name}: {brief.objective[:180]}",
                title=f"AI visual - {brief.brand.name}",
                tags=["ai-generated", brief.provider, brief.format],
            )
            asset.source = f"ai_{brief.provider}"
            asset.processing_status = asset.ProcessingStatus.COMPLETED
            asset.save(update_fields=["source", "processing_status"])
            if brief.post_id:
                PostMedia.objects.get_or_create(
                    post=brief.post, media_asset=asset, defaults={"alt_text": asset.alt_text}
                )
            brief.media_asset = asset
            brief.status = VisualBrief.Status.COMPLETED
            brief.completed_at = timezone.now()
            brief.save(update_fields=["media_asset", "status", "completed_at"])
        return asset
    except (ProviderError, ValueError) as exc:
        brief.status = VisualBrief.Status.FAILED
        brief.error_message = "Image generation failed. Please retry later."
        brief.completed_at = timezone.now()
        brief.save(update_fields=["status", "error_message", "completed_at"])
        raise ProviderError(brief.error_message) from exc
