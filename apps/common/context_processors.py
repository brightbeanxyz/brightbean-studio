"""Context processors for sidebar and global template data."""

from django.db.models import Count, Q


def sidebar_context(request):
    """Inject sidebar data into every template context.

    Provides:
        sidebar_workspaces: list of workspace objects the user belongs to
        sidebar_channels: connected social accounts for the current workspace
        sidebar_connectable_platforms: platforms available to connect
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {}

    from apps.members.models import WorkspaceMembership
    from apps.social_accounts.models import AnalyticsPlatformConfig, PlatformVisibility, SocialAccount

    analytics_enabled_platforms = AnalyticsPlatformConfig.enabled_platforms()

    # User's workspaces (non-archived)
    workspace_memberships = (
        WorkspaceMembership.objects.filter(
            user=request.user,
            workspace__is_archived=False,
        )
        .select_related("workspace")
        .order_by("workspace__name")
    )
    sidebar_workspaces = [wm.workspace for wm in workspace_memberships]

    # Connected channels for the current workspace
    sidebar_channels = []
    sidebar_unhealthy_channels = []
    sidebar_connectable_platforms = []

    workspace = getattr(request, "workspace", None)

    if workspace:
        from apps.composer.models import PlatformPost

        sidebar_channels = list(
            SocialAccount.objects.for_workspace(workspace.id)
            .filter(connection_status=SocialAccount.ConnectionStatus.CONNECTED)
            .annotate(
                queued_post_count=Count(
                    "platform_posts",
                    filter=Q(platform_posts__status=PlatformPost.Status.SCHEDULED),
                )
            )
            .order_by("platform", "account_name")
        )

        sidebar_unhealthy_channels = list(
            SocialAccount.objects.for_workspace(workspace.id)
            .filter(
                connection_status__in=[
                    SocialAccount.ConnectionStatus.DISCONNECTED,
                    SocialAccount.ConnectionStatus.ERROR,
                    SocialAccount.ConnectionStatus.TOKEN_EXPIRING,
                ]
            )
            .order_by("platform", "account_name")
        )

        # Connectable platforms: not yet connected in this workspace.
        # Show all known platforms (configured or not) so the sidebar
        # always surfaces what can be connected. The connect page itself
        # handles the "not configured" case with an admin prompt, and shares
        # PlatformVisibility.visible_choices() with us so the two can't disagree.
        connected_platforms = {ch.platform for ch in sidebar_channels}
        sidebar_connectable_platforms = sorted(
            ((p, label) for p, label in PlatformVisibility.visible_choices() if p not in connected_platforms),
            key=_connect_suggestion_rank,
        )

    # Unread inbox count for sidebar badge
    sidebar_unread_inbox_count = 0
    if workspace:
        from apps.inbox.models import InboxMessage

        sidebar_unread_inbox_count = (
            InboxMessage.objects.for_workspace(workspace.id).filter(status=InboxMessage.Status.UNREAD).count()
        )

    # Pending approval count for badge
    sidebar_pending_approvals = 0
    if workspace:
        from apps.composer.models import PlatformPost

        sidebar_pending_approvals = (
            PlatformPost.objects.filter(
                post__workspace_id=workspace.id,
                status__in=["pending_review", "pending_client"],
            )
            .values("post_id")
            .distinct()
            .count()
        )

    # Idea columns and tags for the quick-create modal in the sidebar
    sidebar_idea_columns = []
    sidebar_idea_tags = []
    if workspace:
        from apps.composer.models import IdeaGroup, Tag

        groups = IdeaGroup.objects.for_workspace(workspace.id).order_by("position", "created_at")
        sidebar_idea_columns = [{"id": str(g.id), "label": g.name} for g in groups] if groups.exists() else []
        sidebar_idea_tags = list(Tag.objects.for_workspace(workspace.id).values_list("name", flat=True))

    # Workspace creation permission (org owners and admins only)
    can_create_workspace = False
    org_membership = getattr(request, "org_membership", None)
    if org_membership and org_membership.org_role in ("owner", "admin"):
        can_create_workspace = True

    return {
        "sidebar_workspaces": sidebar_workspaces,
        "can_create_workspace": can_create_workspace,
        "sidebar_channels": sidebar_channels,
        "sidebar_unhealthy_channels": sidebar_unhealthy_channels,
        "sidebar_connectable_platforms": sidebar_connectable_platforms,
        "sidebar_unread_inbox_count": sidebar_unread_inbox_count,
        "sidebar_pending_approvals": sidebar_pending_approvals,
        "sidebar_idea_columns": sidebar_idea_columns,
        "sidebar_idea_tags": sidebar_idea_tags,
        "analytics_enabled_platforms": analytics_enabled_platforms,
    }


# Display order for the sidebar's connect shortcuts, most-asked-for first.
# The template shows only the first three, and ``Platform.choices`` is ordered
# for the publish pipeline — leaving it to decide would put Facebook, Instagram
# and Instagram (Direct) in all three slots and push LinkedIn/TikTok/YouTube
# out of sight.
#
# Unlike the hand-maintained list this replaced, this is a *ranking*, not the
# set: a platform missing from here still appears (ranked last), so a new
# platform can never be silently hidden from the sidebar again.
_CONNECT_SUGGESTION_ORDER: tuple[str, ...] = (
    "instagram",
    "linkedin_company",
    "tiktok",
    "youtube",
    "facebook",
    "linkedin_personal",
    "threads",
    "pinterest",
    "instagram_login",
    "google_business",
    "bluesky",
    "mastodon",
    "devto",
)


def _connect_suggestion_rank(choice):
    platform, _label = choice
    try:
        return (0, _CONNECT_SUGGESTION_ORDER.index(platform))
    except ValueError:
        return (1, 0)
