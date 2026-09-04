from django.db import transaction
from django.utils import timezone

from apps.brands.services import ensure_strategy_version

from .models import AIProviderConfiguration, GeneratedContent, GenerationRequest
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
    configuration=None,
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
        options = {}
        if configuration:
            options = {
                "api_key": configuration.api_key,
                "base_url": configuration.base_url,
                "timeout": configuration.timeout_seconds,
            }
            model = model or configuration.default_model
        body = generate_text(provider=provider, model=model, system=_context(brand, version), prompt=prompt, **options)
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
        request.attempt_count += 1
        request.input_tokens = max(1, (len(prompt) + len(_context(brand, version))) // 4)
        request.output_tokens = max(1, len(body) // 4)
        request.estimated_cost_usd = _estimate_cost(provider, request.input_tokens, request.output_tokens)
        request.completed_at = timezone.now()
        request.save(
            update_fields=[
                "status", "attempt_count", "input_tokens", "output_tokens", "estimated_cost_usd", "completed_at"
            ]
        )
    return request, output


def _estimate_cost(provider, input_tokens, output_tokens):
    """Conservative display estimate; billing truth remains the provider invoice."""
    per_million = {"openai": (0.15, 0.60), "anthropic": (0.80, 4.00), "gemini": (0.10, 0.40)}
    input_rate, output_rate = per_million.get(provider, (0, 0))
    return (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000


def configured_providers(organization):
    configurations = AIProviderConfiguration.objects.filter(organization=organization, is_enabled=True)
    return [configuration for configuration in configurations if configuration.is_configured]


def enforce_generation_quota(configuration):
    today = timezone.localdate()
    used = GenerationRequest.objects.filter(
        workspace__organization=configuration.organization,
        provider=configuration.provider,
        created_at__date=today,
    ).count()
    if used >= configuration.daily_request_limit:
        raise ValueError("Daily AI generation quota reached for this provider.")


def queue_generation(**kwargs):
    brand = kwargs["brand"]
    provider = kwargs["provider"]
    configuration = AIProviderConfiguration.objects.get(
        organization=brand.workspace.organization, provider=provider, is_enabled=True
    )
    if not configuration.is_configured:
        raise ValueError("AI provider is not configured.")
    enforce_generation_quota(configuration)
    _, version = ensure_strategy_version(brand=brand, user=kwargs["user"])
    request = GenerationRequest.objects.create(
        workspace=brand.workspace,
        brand=brand,
        provider=provider,
        model=kwargs.get("model", "") or configuration.default_model,
        platform=kwargs["platform"],
        content_type=kwargs["content_type"],
        audience=kwargs.get("audience", ""),
        context={
            "instruction": kwargs.get("instruction", ""),
            "previous_content": kwargs.get("previous_content") or [],
            "analytics": kwargs.get("analytics") or {},
            "strategy_version": version.version,
        },
        requested_by=kwargs["user"],
    )
    from .tasks import run_generation

    run_generation(str(request.id))
    return request


def process_queued_generation(request_id):
    request = GenerationRequest.objects.select_related("brand", "requested_by", "workspace__organization").get(
        id=request_id
    )
    if request.status == GenerationRequest.Status.COMPLETED:
        return request.outputs.first()
    configuration = AIProviderConfiguration.objects.get(
        organization=request.workspace.organization, provider=request.provider, is_enabled=True
    )
    request.status = GenerationRequest.Status.PROCESSING
    request.attempt_count += 1
    request.save(update_fields=["status", "attempt_count"])
    context = request.context or {}
    _, version = ensure_strategy_version(brand=request.brand, user=request.requested_by)
    prompt = (
        f"Create one {request.content_type} for {request.platform}. Audience: {request.audience or 'the brand audience'}. "
        f"Instruction: {context.get('instruction') or 'Create a useful, specific post.'} "
        f"Previous content: {context.get('previous_content') or 'None'}. Analytics: {context.get('analytics') or 'None'}. "
        "Include a clear hook and CTA. Return plain text for human review."
    )
    try:
        body = generate_text(
            provider=request.provider, model=request.model, system=_context(request.brand, version), prompt=prompt,
            api_key=configuration.api_key, base_url=configuration.base_url, timeout=configuration.timeout_seconds,
        )
    except (ProviderError, ValueError) as exc:
        request.status = GenerationRequest.Status.FAILED
        request.error_message = "AI provider request failed. Please retry later."
        request.completed_at = timezone.now()
        request.save(update_fields=["status", "error_message", "completed_at"])
        raise ProviderError(request.error_message) from exc
    with transaction.atomic():
        output = GeneratedContent.objects.create(
            request=request, workspace=request.workspace, brand=request.brand, platform=request.platform,
            content_type=request.content_type, body=body,
            metadata={"strategy_version": version.version, "provider": request.provider, "model": request.model},
        )
        request.status = GenerationRequest.Status.COMPLETED
        request.input_tokens = max(1, (len(prompt) + len(_context(request.brand, version))) // 4)
        request.output_tokens = max(1, len(body) // 4)
        request.estimated_cost_usd = _estimate_cost(request.provider, request.input_tokens, request.output_tokens)
        request.completed_at = timezone.now()
        request.save(update_fields=["status", "input_tokens", "output_tokens", "estimated_cost_usd", "completed_at"])
    return output


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
        origin=Post.Origin.AI,
        brand=locked_output.brand,
        campaign=locked_output.campaign,
        title=locked_output.title or f"AI draft - {locked_output.brand.name}",
        caption=locked_output.body,
        internal_notes=f"Generated with {locked_output.request.provider} via Social Content AI.",
    )
    locked_output.composer_post = post
    locked_output.save(update_fields=["composer_post"])
    output.composer_post = post
    return post, True


@transaction.atomic
def create_composer_draft_from_plan_item(*, item_id, workspace, user):
    """Materialize one editorial plan item as an idempotent Composer draft."""
    from datetime import datetime, time
    from zoneinfo import ZoneInfo

    from apps.composer.models import Post

    from .models import ContentPlanItem

    item = (
        ContentPlanItem.objects.select_for_update()
        .select_related("plan__brand", "plan__campaign", "composer_post")
        .get(id=item_id, plan__workspace=workspace)
    )
    if item.composer_post_id:
        return item.composer_post, False
    hashtags = " ".join(str(value) for value in (item.hashtags or []))
    sections = [part for part in (item.hook, item.topic, item.cta, hashtags) if part]
    try:
        tz = ZoneInfo(workspace.effective_timezone or "UTC")
    except (KeyError, ValueError):
        tz = ZoneInfo("UTC")
    proposed = timezone.make_aware(datetime.combine(item.planned_for, time(9)), timezone=tz)
    post = Post.objects.create(
        workspace=workspace,
        author=user,
        origin=Post.Origin.PLAN,
        brand=item.plan.brand,
        campaign=item.plan.campaign,
        title=item.topic,
        caption="\n\n".join(sections),
        tags=list(item.keywords or []),
        proposed_publish_at=proposed,
        internal_notes=(
            f"Created from editorial plan item {item.id}. Recommended format: {item.recommended_format}; "
            f"platform: {item.recommended_platform}."
        ),
    )
    item.composer_post = post
    item.save(update_fields=["composer_post"])
    return post, True
