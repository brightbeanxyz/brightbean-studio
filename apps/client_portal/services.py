"""Client Portal business logic.

Handles magic link generation, verification, and portal session creation.
"""

import logging

from django.conf import settings
from django.contrib.auth import login
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.members.models import WorkspaceMembership

from .models import MagicLinkToken

logger = logging.getLogger(__name__)


def generate_magic_link(workspace, client_user, created_by):
    """Generate a magic link for a client user and send it via email.

    Args:
        workspace: The Workspace the client belongs to.
        client_user: The User with client role.
        created_by: The User (manager) who initiated the generation.

    Returns:
        The created MagicLinkToken.
    """
    # Validate client has client role in workspace
    membership = WorkspaceMembership.objects.filter(
        user=client_user,
        workspace=workspace,
        workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
    ).first()

    if not membership:
        raise ValueError("User does not have client role in this workspace.")

    # Invalidate any existing non-expired tokens for this user+workspace
    MagicLinkToken.objects.filter(
        user=client_user,
        workspace=workspace,
        is_consumed=False,
        expires_at__gt=timezone.now(),
    ).update(expires_at=timezone.now())

    # Create new token
    token = MagicLinkToken.objects.create(
        user=client_user,
        workspace=workspace,
    )

    # Build magic link URL
    app_url = getattr(settings, "APP_URL", "http://localhost:8000").rstrip("/")
    magic_url = f"{app_url}/portal/{token.token}/"

    # Send email
    context = {
        "client_user": client_user,
        "workspace": workspace,
        "magic_url": magic_url,
        "created_by": created_by,
        "app_url": app_url,
    }

    subject = f"{workspace.name} - Posts ready for your review"
    text_content = render_to_string("client_portal/email/magic_link.txt", context)
    html_content = render_to_string("client_portal/email/magic_link.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@localhost"),
        to=[client_user.email],
    )
    msg.attach_alternative(html_content, "text/html")

    try:
        msg.send(fail_silently=False)
    except Exception:
        logger.exception("Failed to send magic link email to %s", client_user.email)

    return token


def peek_magic_link(token_string):
    """Validate a magic link token *without* consuming it.

    Used to render the confirmation page on GET so that email link scanners
    that prefetch the URL cannot burn the one-time token. Returns the
    MagicLinkToken when it is valid and unused, otherwise None.
    """
    try:
        token = MagicLinkToken.objects.select_related("user", "workspace").get(token=token_string)
    except MagicLinkToken.DoesNotExist:
        return None

    if token.is_expired or token.is_consumed:
        return None

    return token


def consume_magic_link(token_string):
    """Validate and atomically consume a magic link token (single-use).

    Returns:
        (user, workspace, is_valid) tuple.
        If missing/expired/already consumed: (None, None, False).
    """
    try:
        token = MagicLinkToken.objects.select_related("user", "workspace").get(token=token_string)
    except MagicLinkToken.DoesNotExist:
        return None, None, False

    if token.is_expired:
        return None, None, False

    # Atomic single-use: only the request that flips is_consumed False->True wins.
    consumed = MagicLinkToken.objects.filter(pk=token.pk, is_consumed=False).update(
        is_consumed=True,
        last_used_at=timezone.now(),
    )
    if not consumed:
        return None, None, False

    return token.user, token.workspace, True


def revoke_magic_link(token_id, workspace):
    """Revoke an active magic link by expiring it immediately."""
    MagicLinkToken.objects.filter(
        id=token_id,
        workspace=workspace,
        expires_at__gt=timezone.now(),
    ).update(expires_at=timezone.now())


def create_portal_session(request, user, workspace):
    """Create a portal session for the client user.

    Logs in the user and sets portal-specific session variables.
    """
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["is_portal_session"] = True
    request.session["portal_workspace_id"] = str(workspace.id)
    # 30-day session
    request.session.set_expiry(30 * 24 * 60 * 60)
