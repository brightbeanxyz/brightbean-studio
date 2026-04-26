"""Background tasks for organization lifecycle."""

import logging

from background_task import background
from django.utils import timezone

from .models import Organization

logger = logging.getLogger(__name__)


@background(schedule=0)
def execute_scheduled_org_deletion(org_id):
    """Delete an org whose 14-day grace period has elapsed.

    Idempotent and cancellation-safe: re-reads the current state and bails
    out if the org is already gone, the user cancelled deletion, or the
    scheduled datetime is still in the future.
    """
    try:
        org = Organization.objects.get(pk=org_id)
    except Organization.DoesNotExist:
        logger.info("org %s already gone, nothing to purge", org_id)
        return

    if not org.deletion_requested_at or not org.deletion_scheduled_for:
        logger.info("org %s has no pending deletion; user must have cancelled", org_id)
        return

    if org.deletion_scheduled_for > timezone.now():
        logger.info("org %s scheduled_for is in the future; skipping this run", org_id)
        return

    org_name = org.name
    org.hard_delete()
    logger.info('org "%s" (%s) purged after grace period', org_name, org_id)
