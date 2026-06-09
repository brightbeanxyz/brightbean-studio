"""Onboarding checklist evaluation logic.

Computes the 5 checklist items and their completion status for a workspace.
Used by the workspace dashboard to render the dynamic "Get Started" card.
"""

from django.urls import reverse


def get_checklist_items(workspace):
    """Return a list of checklist item dicts with dynamic completion status.

    Each item has: key, title, description, completed (bool), url, icon_color, icon_svg

    SECURITY: `icon_svg` is rendered with `|safe` in the checklist template.
    It MUST remain a server-side constant string. Never populate it from user
    input, model fields, or any other untrusted source.
    """
    from apps.composer.models import Idea, Post
    from apps.members.models import WorkspaceMembership
    from apps.social_accounts.models import SocialAccount

    workspace_id = workspace.id

    items = [
        {
            "key": "connect_accounts",
            "title": "Connect social accounts",
            "description": "Link your Instagram, LinkedIn, or other platforms",
            "completed": SocialAccount.objects.for_workspace(workspace_id).exists(),
            "url": reverse(
                "social_accounts:connect",
                kwargs={"workspace_id": workspace_id},
            ),
            "icon_color": "sky",
            "icon_svg": '<path d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101"/><path d="M10.172 13.828a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>',
        },
        {
            "key": "create_post",
            "title": "Create your first post",
            "description": "Draft and schedule content for your audience",
            "completed": Post.objects.for_workspace(workspace_id).exists(),
            "url": reverse(
                "composer:compose",
                kwargs={"workspace_id": workspace_id},
            ),
            "icon_color": "sky",
            "icon_svg": '<path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>',
        },
        {
            "key": "create_idea",
            "title": "Create your first idea",
            "description": "Capture content ideas to develop later",
            "completed": Idea.objects.for_workspace(workspace_id).filter(author__isnull=False).exists(),
            "url": reverse(
                "composer:create_landing",
                kwargs={"workspace_id": workspace_id},
            ),
            "icon_color": "sky",
            "icon_svg": '<path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>',
        },
        {
            "key": "invite_members",
            "title": "Invite your team",
            "description": "Add team members to collaborate on content",
            "completed": WorkspaceMembership.objects.filter(
                workspace_id=workspace_id,
                workspace_role=WorkspaceMembership.WorkspaceRole.CLIENT,
            ).exists(),
            "url": reverse("members:list"),
            "icon_color": "sky",
            "icon_svg": '<path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="8.5" cy="7" r="4"/><path d="M20 8v6m3-3h-6"/>',
        },
    ]
    return items
