import uuid

from django.db import models


class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    logo_url = models.URLField(blank=True, default="")
    default_timezone = models.CharField(max_length=63, default="UTC")

    # Deletion workflow
    deletion_requested_at = models.DateTimeField(blank=True, null=True)
    deletion_scheduled_for = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations_organization"

    def __str__(self):
        return self.name

    @property
    def is_deletion_pending(self):
        return self.deletion_requested_at is not None and self.deleted_at is None

    def hard_delete(self, requesting_user=None):
        """Hard-delete this org and settle every member's account.

        - `requesting_user` (optional): the user who triggered the immediate-
          delete flow. Their account is deleted along with the org so they
          get a truly fresh start on re-signup. Pass `None` (the default) for
          the scheduled-grace-period path and the management-command sweeper
          — those don't carry request context and we don't want to silently
          delete accounts from a background job.
        - Every other member gets a freshly provisioned default "My
          Organization" + "My Workspace" so they land on a working dashboard
          instead of limbo on next login.
        - Any user's `last_workspace_id` that points at a workspace in this
          org is nulled first (defensive; provision-for-member would reset it
          anyway, but the delete_user path wouldn't).
        """
        from apps.accounts.models import User
        from apps.accounts.signals import provision_organization_and_workspace
        from apps.members.models import OrgMembership
        from apps.workspaces.models import Workspace

        member_ids = list(OrgMembership.objects.filter(organization=self).values_list("user_id", flat=True))
        ws_ids = list(Workspace.objects.filter(organization=self).values_list("id", flat=True))

        if ws_ids:
            User.objects.filter(last_workspace_id__in=ws_ids).update(last_workspace_id=None)

        self.delete()  # CASCADE: workspaces, memberships, credentials, media, etc.

        requesting_user_id = requesting_user.pk if requesting_user else None
        for uid in member_ids:
            if uid == requesting_user_id:
                User.objects.filter(pk=uid).delete()
                continue
            try:
                user = User.objects.get(pk=uid)
            except User.DoesNotExist:
                continue
            provision_organization_and_workspace(user)
