package com.brightbean.studio.application.auth

import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.WorkspaceRole

object WorkspacePermissionKeys {
    const val CREATE_POSTS = "create_posts"
    const val EDIT_OTHERS_POSTS = "edit_others_posts"
    const val APPROVE_POSTS = "approve_posts"
    const val PUBLISH_DIRECTLY = "publish_directly"
    const val MANAGE_SOCIAL_ACCOUNTS = "manage_social_accounts"
    const val VIEW_ANALYTICS = "view_analytics"
    const val USE_INBOX = "use_inbox"
    const val REPLY_FROM_INBOX = "reply_from_inbox"
    const val MANAGE_WORKSPACE_SETTINGS = "manage_workspace_settings"
    const val UPLOAD_MEDIA = "upload_media"
    const val EDIT_MEDIA = "edit_media"
    const val DELETE_MEDIA = "delete_media"
    const val MANAGE_MEDIA = "manage_media"

    val ALL = listOf(
        CREATE_POSTS, EDIT_OTHERS_POSTS, APPROVE_POSTS, PUBLISH_DIRECTLY,
        MANAGE_SOCIAL_ACCOUNTS, VIEW_ANALYTICS, USE_INBOX, REPLY_FROM_INBOX,
        MANAGE_WORKSPACE_SETTINGS, UPLOAD_MEDIA, EDIT_MEDIA, DELETE_MEDIA,
        MANAGE_MEDIA,
    )
}

object OrgPermissionKeys {
    const val MANAGE_INTELLIGENCE_BILLING = "manage_intelligence_billing"
    const val USE_INTELLIGENCE = "use_intelligence"
    const val MANAGE_API_KEYS = "manage_api_keys"

    val ALL = listOf(MANAGE_INTELLIGENCE_BILLING, USE_INTELLIGENCE, MANAGE_API_KEYS)
}

val BUILTIN_ORG_PERMISSIONS: Map<OrgRole, Set<String>> = mapOf(
    OrgRole.OWNER to setOf(
        OrgPermissionKeys.MANAGE_INTELLIGENCE_BILLING,
        OrgPermissionKeys.USE_INTELLIGENCE,
        OrgPermissionKeys.MANAGE_API_KEYS,
    ),
    OrgRole.ADMIN to setOf(
        OrgPermissionKeys.MANAGE_INTELLIGENCE_BILLING,
        OrgPermissionKeys.USE_INTELLIGENCE,
        OrgPermissionKeys.MANAGE_API_KEYS,
    ),
    OrgRole.MEMBER to setOf(
        OrgPermissionKeys.USE_INTELLIGENCE,
    ),
)

val BUILTIN_WORKSPACE_PERMISSIONS: Map<WorkspaceRole, Set<String>> = mapOf(
    WorkspaceRole.OWNER to WorkspacePermissionKeys.ALL.toSet(),
    WorkspaceRole.MANAGER to WorkspacePermissionKeys.ALL.toSet() - WorkspacePermissionKeys.MANAGE_WORKSPACE_SETTINGS,
    WorkspaceRole.EDITOR to setOf(
        WorkspacePermissionKeys.CREATE_POSTS,
        WorkspacePermissionKeys.EDIT_OTHERS_POSTS,
        WorkspacePermissionKeys.VIEW_ANALYTICS,
        WorkspacePermissionKeys.USE_INBOX,
        WorkspacePermissionKeys.REPLY_FROM_INBOX,
        WorkspacePermissionKeys.UPLOAD_MEDIA,
        WorkspacePermissionKeys.EDIT_MEDIA,
    ),
    WorkspaceRole.CONTRIBUTOR to setOf(
        WorkspacePermissionKeys.CREATE_POSTS,
        WorkspacePermissionKeys.VIEW_ANALYTICS,
        WorkspacePermissionKeys.UPLOAD_MEDIA,
        WorkspacePermissionKeys.EDIT_MEDIA,
    ),
    WorkspaceRole.CLIENT to setOf(
        WorkspacePermissionKeys.APPROVE_POSTS,
        WorkspacePermissionKeys.VIEW_ANALYTICS,
    ),
    WorkspaceRole.VIEWER to setOf(
        WorkspacePermissionKeys.VIEW_ANALYTICS,
    ),
)

val ORG_ROLE_LEVEL: Map<OrgRole, Int> = mapOf(
    OrgRole.OWNER to 3,
    OrgRole.ADMIN to 2,
    OrgRole.MEMBER to 1,
)

val WORKSPACE_ROLE_LEVEL: Map<WorkspaceRole, Int> = mapOf(
    WorkspaceRole.OWNER to 6,
    WorkspaceRole.MANAGER to 5,
    WorkspaceRole.EDITOR to 4,
    WorkspaceRole.CONTRIBUTOR to 3,
    WorkspaceRole.CLIENT to 2,
    WorkspaceRole.VIEWER to 1,
)
