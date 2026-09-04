import logging

from background_task import background

from .generation import process_queued_generation
from .models import AIProviderConfiguration, GenerationRequest
from .providers import ProviderError

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
