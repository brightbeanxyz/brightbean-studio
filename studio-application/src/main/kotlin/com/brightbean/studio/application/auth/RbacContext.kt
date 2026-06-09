package com.brightbean.studio.application.auth

import com.brightbean.studio.domain.model.OrgMembership
import com.brightbean.studio.domain.model.User
import com.brightbean.studio.domain.model.WorkspaceMembership

data class RbacContext(
    val user: User,
    val orgMembership: OrgMembership?,
    val workspaceMembership: WorkspaceMembership?,
    val effectivePermissions: Map<String, Boolean>,
)
