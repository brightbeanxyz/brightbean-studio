from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from PIL import Image


def health_check(request):
    """Health check endpoint at /health/."""
    return JsonResponse({"status": "ok"})


@login_required
def dashboard(request):
    """Main dashboard - redirects to last used workspace or shows org overview."""
    from apps.members.models import WorkspaceMembership

    user = request.user

    # Only trust last_workspace_id if the user still has an active membership
    # in that workspace. Otherwise the org may have been deleted out from under
    # them and we'd redirect into a 403.
    if user.last_workspace_id:
        if WorkspaceMembership.objects.filter(
            user=user,
            workspace_id=user.last_workspace_id,
            workspace__is_archived=False,
        ).exists():
            return redirect("calendar:calendar", workspace_id=user.last_workspace_id)
        user.last_workspace_id = None
        user.save(update_fields=["last_workspace_id"])

    # Fallback: try to find any workspace the user belongs to
    membership = (
        WorkspaceMembership.objects.filter(user=user, workspace__is_archived=False).select_related("workspace").first()
    )
    if membership:
        user.last_workspace_id = membership.workspace.id
        user.save(update_fields=["last_workspace_id"])
        return redirect("calendar:calendar", workspace_id=membership.workspace.id)

    return render(request, "accounts/dashboard.html")


@login_required
@require_http_methods(["GET", "POST"])
def account_settings(request):
    user = request.user
    tab = request.GET.get("tab", "profile")
    settings_active = "preferences" if tab == "preferences" else "profile"

    if request.method == "POST":
        action = request.POST.get("action", "")

        if action == "update_photo":
            _handle_photo_update(request, user)
        elif action == "update_name":
            _handle_name_update(request, user)
        elif action == "update_password":
            _handle_password_update(request, user)
        elif action == "delete_account":
            return _handle_account_deletion(request, user)

        return redirect("accounts:settings")

    # Fetch the user's organization membership for role display
    from apps.members.models import OrgMembership

    org_membership = OrgMembership.objects.filter(user=user).select_related("organization").first()

    return render(
        request,
        "accounts/settings.html",
        {
            "settings_active": settings_active,
            "org_membership": org_membership,
        },
    )


def _handle_photo_update(request, user):
    """Handle avatar upload or deletion."""
    # Handle deletion
    if request.POST.get("delete_photo") == "1":
        if user.avatar:
            user.avatar.delete(save=False)
        user.save()
        messages.success(request, "Photo removed.")
        return

    # Handle upload
    if "avatar" not in request.FILES:
        return

    avatar = request.FILES["avatar"]

    # Validate file type
    allowed_types = ("image/jpeg", "image/png", "image/webp", "image/gif")
    if avatar.content_type not in allowed_types:
        messages.error(request, "Photo must be a JPEG, PNG, WebP, or GIF image.")
        return

    # Validate file size (2 MB max)
    max_size = 2 * 1024 * 1024
    if avatar.size > max_size:
        messages.error(request, "Photo must be under 2 MB.")
        return

    # Validate minimum dimensions (180x180)
    try:
        img = Image.open(avatar)
        width, height = img.size
        if width < 180 or height < 180:
            messages.error(request, "Photo must be at least 180×180 pixels.")
            return
    except Exception:
        messages.error(request, "Could not read image file.")
        return
    finally:
        avatar.seek(0)  # Reset file pointer after reading

    # Delete old avatar before saving new one
    if user.avatar:
        user.avatar.delete(save=False)

    user.avatar = avatar
    user.save()
    messages.success(request, "Photo updated.")


def _handle_name_update(request, user):
    """Handle name change."""
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name cannot be empty.")
        return

    user.name = name
    user.save(update_fields=["name"])
    messages.success(request, "Name updated.")


def _handle_password_update(request, user):
    """Handle password change."""
    current_password = request.POST.get("current_password", "")
    password = request.POST.get("password", "")
    password_confirm = request.POST.get("password_confirm", "")

    if not current_password:
        messages.error(request, "Current password is required.")
        return

    if not user.check_password(current_password):
        messages.error(request, "Current password is incorrect.")
        return

    if not password:
        messages.error(request, "New password cannot be empty.")
        return

    if len(password) < 8:
        messages.error(request, "New password must be at least 8 characters.")
        return

    if password != password_confirm:
        messages.error(request, "New passwords do not match.")
        return

    user.set_password(password)
    user.save()
    update_session_auth_hash(request, user)
    messages.success(request, "Password changed.")


def _handle_account_deletion(request, user):
    """Handle account deletion with sole-owner safety check."""
    from apps.members.models import OrgMembership

    # Check if user is the sole owner of any organization
    owned_memberships = OrgMembership.objects.filter(user=user, org_role=OrgMembership.OrgRole.OWNER).select_related(
        "organization"
    )

    sole_owner_orgs = []
    for membership in owned_memberships:
        other_owners = (
            OrgMembership.objects.filter(
                organization=membership.organization,
                org_role=OrgMembership.OrgRole.OWNER,
            )
            .exclude(user=user)
            .exists()
        )
        if not other_owners:
            sole_owner_orgs.append(membership.organization.name)

    if sole_owner_orgs:
        org_names = ", ".join(sole_owner_orgs)
        messages.error(
            request,
            f"You are the sole owner of: {org_names}. "
            "Transfer ownership or delete the organization before deleting your account.",
        )
        return redirect("accounts:settings")

    # Safe to delete
    user.delete()
    logout(request)
    messages.success(request, "Your account has been deleted.")
    return redirect("account_login")


@login_required
@require_http_methods(["GET", "POST"])
def accept_terms(request):
    """Terms of Service acceptance page for social signup users."""
    if request.user.tos_accepted_at is not None:
        return redirect("/")

    if request.method == "POST":
        if request.POST.get("agree"):
            request.user.tos_accepted_at = timezone.now()
            request.user.save(update_fields=["tos_accepted_at"])
            return redirect("/")
        messages.error(request, "You must agree to the Terms of Service and Privacy Policy to continue.")

    return render(request, "account/accept_terms.html")


def logout_view(request):
    logout(request)
    return redirect("account_login")
