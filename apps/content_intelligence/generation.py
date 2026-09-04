from django.db import transaction
from django.utils import timezone

from apps.brands.services import ensure_strategy_version

from .models import GeneratedContent, GenerationRequest
from .providers import ProviderError, generate_text


def _context(brand, version):
    return (
        f"Brand: {brand.name}\nIndustry: {brand.industry}\nVoice: {brand.brand_voice}\nTone: {brand.tone}\n"
        f"Positioning: {brand.positioning}\nValue proposition: {brand.value_proposition}\n"
        f"Preferred terminology: {', '.join(brand.preferred_terminology)}\nProhibited terms: {', '.join(brand.prohibited_terms)}\n"
        f"Content pillars: {', '.join(brand.content_pillars)}\nEditorial mix: Reach {version.reach_percentage}%, Authority {version.authority_percentage}%, Conversion {version.conversion_percentage}%"
    )


def request_generation(
    *,
    brand,
    provider,
    platform,
    content_type,
    user,
    model="",
    audience="",
    instruction="",
    previous_content=None,
    analytics=None,
):
    if provider not in GenerationRequest.Provider.values:
        raise ValueError("Unsupported AI provider.")
    _, version = ensure_strategy_version(brand=brand, user=user)
    context = {
        "instruction": instruction,
        "previous_content": previous_content or [],
        "analytics": analytics or {},
        "strategy_version": version.version,
    }
    request = GenerationRequest.objects.create(
        workspace=brand.workspace,
        brand=brand,
        provider=provider,
        model=model,
        platform=platform,
        content_type=content_type,
        audience=audience,
        context=context,
        requested_by=user,
        status=GenerationRequest.Status.PROCESSING,
    )
    prompt = (
        f"Create one {content_type} for {platform}. Audience: {audience or 'the brand audience'}. "
        f"Instruction: {instruction or 'Create a useful, specific post.'} Previous content: {previous_content or 'None'}. "
        f"Analytics: {analytics or 'None'}. Include a clear hook and CTA. Return plain text for human review."
    )
    try:
        body = generate_text(provider=provider, model=model, system=_context(brand, version), prompt=prompt)
    except (ProviderError, ValueError) as exc:
        request.status = GenerationRequest.Status.FAILED
        request.error_message = str(exc)
        request.completed_at = timezone.now()
        request.save(update_fields=["status", "error_message", "completed_at"])
        raise
    with transaction.atomic():
        output = GeneratedContent.objects.create(
            request=request,
            workspace=brand.workspace,
            brand=brand,
            platform=platform,
            content_type=content_type,
            body=body,
            metadata={"strategy_version": version.version, "provider": provider, "model": model},
        )
        request.status = GenerationRequest.Status.COMPLETED
        request.completed_at = timezone.now()
        request.save(update_fields=["status", "completed_at"])
    return request, output


@transaction.atomic
def create_composer_draft(*, output, user):
    """Create one editable Composer post from a generated output, idempotently."""
    from apps.composer.models import Post

    locked_output = GeneratedContent.objects.select_for_update().select_related("brand").get(pk=output.pk)
    if locked_output.composer_post_id:
        return locked_output.composer_post, False
    post = Post.objects.create(
        workspace=locked_output.workspace,
        author=user,
        title=locked_output.title or f"AI draft - {locked_output.brand.name}",
        caption=locked_output.body,
        internal_notes=f"Generated with {locked_output.request.provider} via Social Content AI.",
    )
    locked_output.composer_post = post
    locked_output.save(update_fields=["composer_post"])
    output.composer_post = post
    return post, True
