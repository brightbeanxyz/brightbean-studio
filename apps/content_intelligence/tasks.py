import logging

from background_task import background

from .generation import process_queued_generation
from .models import AIProviderConfiguration, GenerationRequest
from .providers import ProviderError
from .visuals import process_visual_brief

logger = logging.getLogger(__name__)


@background(schedule=0)
def run_generation(request_id):
    try:
        process_queued_generation(request_id)
    except (GenerationRequest.DoesNotExist, AIProviderConfiguration.DoesNotExist):
        logger.warning("AI generation request or configuration no longer exists: %s", request_id)
    except ProviderError:
        request = GenerationRequest.objects.filter(id=request_id).first()
        if not request:
            return
        configuration = AIProviderConfiguration.objects.filter(
            organization=request.workspace.organization, provider=request.provider
        ).first()
        if configuration and request.attempt_count <= configuration.max_retries:
            request.status = GenerationRequest.Status.PENDING
            request.save(update_fields=["status"])
            run_generation(request_id, schedule=60 * request.attempt_count)


@background(schedule=0)
def run_visual_generation(brief_id):
    try:
        process_visual_brief(brief_id)
    except ProviderError:
        from .models import VisualBrief

        brief = VisualBrief.objects.filter(id=brief_id).select_related("workspace__organization").first()
        if not brief:
            return
        configuration = AIProviderConfiguration.objects.filter(
            organization=brief.workspace.organization, provider=brief.provider
        ).first()
        if configuration and brief.attempt_count <= configuration.max_retries:
            brief.status = VisualBrief.Status.PENDING
            brief.save(update_fields=["status"])
            run_visual_generation(brief_id, schedule=60 * brief.attempt_count)
