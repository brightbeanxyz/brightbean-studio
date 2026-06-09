CREATE TABLE IF NOT EXISTS analytics_account_insights_snapshot (
    id UUID PRIMARY KEY,
    social_account_id UUID NOT NULL,
    metric_key VARCHAR(40) NOT NULL,
    date DATE NOT NULL,
    value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(social_account_id, metric_key, date)
);

CREATE TABLE IF NOT EXISTS analytics_post_insights_snapshot (
    id UUID PRIMARY KEY,
    platform_post_id UUID NOT NULL,
    metric_key VARCHAR(40) NOT NULL,
    date DATE NOT NULL,
    value DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    captured_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(platform_post_id, metric_key, date)
);

CREATE INDEX IF NOT EXISTS idx_analytics_post_date ON analytics_post_insights_snapshot(platform_post_id, date);

CREATE TABLE IF NOT EXISTS client_portal_magic_link_token (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    token VARCHAR(128) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_consumed BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_magic_user_ws ON client_portal_magic_link_token(user_id, workspace_id);

CREATE TABLE IF NOT EXISTS onboarding_connection_link (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    token VARCHAR(255) NOT NULL UNIQUE,
    created_by UUID,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS onboarding_connection_link_usage (
    id UUID PRIMARY KEY,
    connection_link_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    connected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(connection_link_id, social_account_id)
);

CREATE TABLE IF NOT EXISTS onboarding_checklist (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    workspace_id UUID NOT NULL,
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, workspace_id)
);

CREATE TABLE IF NOT EXISTS api_keys_api_key (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    lookup_prefix VARCHAR(16) NOT NULL UNIQUE,
    token_hash VARCHAR(64) NOT NULL,
    permissions TEXT NOT NULL DEFAULT '[]',
    social_account_ids TEXT NOT NULL DEFAULT '[]',
    issued_by UUID,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    last_used_ip VARCHAR(45),
    rate_override_writes INT,
    rate_override_reads INT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_apikey_ws_revoked ON api_keys_api_key(workspace_id, revoked_at);

CREATE TABLE IF NOT EXISTS api_keys_audit_log (
    id UUID PRIMARY KEY,
    api_key_id UUID NOT NULL,
    action VARCHAR(64) NOT NULL,
    target_id UUID,
    method VARCHAR(10) NOT NULL,
    path VARCHAR(255) NOT NULL,
    status_code SMALLINT NOT NULL,
    ip VARCHAR(45),
    user_agent VARCHAR(512) NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_key_time ON api_keys_audit_log(api_key_id, created_at);
