package com.brightbean.studio.web.server

import com.brightbean.studio.application.auth.ORG_ROLE_LEVEL
import com.brightbean.studio.application.auth.RbacContext
import com.brightbean.studio.application.auth.WORKSPACE_ROLE_LEVEL
import com.brightbean.studio.domain.model.OrgRole
import com.brightbean.studio.domain.model.WorkspaceRole
import com.sun.net.httpserver.HttpExchange

object PermissionChecks {
    fun getRbacContext(exchange: HttpExchange): RbacContext? {
        return exchange.getAttribute(RBACMiddleware.RBAC_CONTEXT_ATTR) as? RbacContext
    }

    fun hasPermission(exchange: HttpExchange, key: String): Boolean {
        val context = getRbacContext(exchange) ?: return true
        return context.effectivePermissions[key] == true
    }

    fun hasOrgRole(exchange: HttpExchange, minRole: OrgRole): Boolean {
        val context = getRbacContext(exchange) ?: return false
        val membership = context.orgMembership ?: return false
        val currentLevel = ORG_ROLE_LEVEL[membership.orgRole] ?: 0
        val requiredLevel = ORG_ROLE_LEVEL[minRole] ?: 0
        return currentLevel >= requiredLevel
    }

    fun requireWorkspaceRole(exchange: HttpExchange, minRole: WorkspaceRole): Boolean {
        val context = getRbacContext(exchange) ?: return false
        val membership = context.workspaceMembership ?: return false
        val currentLevel = WORKSPACE_ROLE_LEVEL[membership.workspaceRole] ?: 0
        val requiredLevel = WORKSPACE_ROLE_LEVEL[minRole] ?: 0
        return currentLevel >= requiredLevel
    }
}
