DROP TABLE IF EXISTS organization;
CREATE TABLE organization (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    logo_url VARCHAR(1024),
    default_timezone VARCHAR(63) NOT NULL DEFAULT 'UTC',
    billing_email VARCHAR(255) NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

ALTER TABLE workspace ADD COLUMN organization_id UUID;
ALTER TABLE workspace ADD COLUMN is_archived BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE org_membership (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    org_role VARCHAR(20) NOT NULL DEFAULT 'MEMBER',
    invited_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, organization_id)
);

CREATE TABLE workspace_membership (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    workspace_role VARCHAR(20) NOT NULL DEFAULT 'VIEWER',
    custom_role_id UUID,
    added_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(user_id, workspace_id)
);

CREATE TABLE custom_role (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    permissions TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(organization_id, name)
);

CREATE TABLE invitation (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    email VARCHAR(255) NOT NULL,
    org_role VARCHAR(20) NOT NULL DEFAULT 'MEMBER',
    workspace_assignments TEXT NOT NULL,
    invited_by UUID,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    accepted_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_org_membership_user ON org_membership(user_id);
CREATE INDEX idx_org_membership_org ON org_membership(organization_id);
CREATE INDEX idx_workspace_membership_user ON workspace_membership(user_id);
CREATE INDEX idx_workspace_membership_workspace ON workspace_membership(workspace_id);
CREATE INDEX idx_custom_role_org ON custom_role(organization_id);
CREATE INDEX idx_invitation_org ON invitation(organization_id);
CREATE INDEX idx_invitation_token ON invitation(token);
CREATE INDEX idx_invitation_status ON invitation(status);
