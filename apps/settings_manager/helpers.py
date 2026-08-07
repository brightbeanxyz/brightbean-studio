"""Settings cascade helper: workspace -> org -> deployment default -> app default."""

from .defaults import APP_DEFAULTS
from .models import OrgSetting, WorkspaceSetting

# Distinguishes "no deployment default supplied" from an explicit None, which is
# a legitimate value for keys like notifications.quiet_hours_start.
_UNSET = object()


def get_setting(workspace_id, key, workspace_org_id=None, default=_UNSET):
    """Return the setting value following the cascade:
    workspace override -> org override -> caller default -> application default.

    Args:
        workspace_id: UUID of the workspace
        key: Setting key (e.g., "approval.internal_reminder_hours")
        workspace_org_id: Optional org ID to avoid an extra query.
                         If not provided, it will be looked up.
        default: Deployment-level default (typically a Django setting backed by
                 an env var) used when no workspace or org override exists.
                 Without it, APP_DEFAULTS is the floor and an operator's env var
                 could never take effect for a workspace that simply has no
                 override row.
    """

    def _fallback():
        return APP_DEFAULTS.get(key) if default is _UNSET else default

    # 1. Check workspace-level override
    try:
        ws_setting = WorkspaceSetting.objects.get(workspace_id=workspace_id, key=key)
        if ws_setting.value is not None:
            return ws_setting.value
    except WorkspaceSetting.DoesNotExist:
        pass

    # 2. Check org-level override
    if workspace_org_id is None:
        from apps.workspaces.models import Workspace

        try:
            workspace_org_id = Workspace.objects.values_list("organization_id", flat=True).get(id=workspace_id)
        except Workspace.DoesNotExist:
            return _fallback()

    try:
        org_setting = OrgSetting.objects.get(organization_id=workspace_org_id, key=key)
        return org_setting.value
    except OrgSetting.DoesNotExist:
        pass

    # 3. Fall back to the deployment default, then the application default
    return _fallback()
