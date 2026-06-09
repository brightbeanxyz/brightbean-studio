CREATE TABLE IF NOT EXISTS platform_credential (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    platform VARCHAR(30) NOT NULL,
    credentials TEXT NOT NULL,
    is_configured BOOLEAN NOT NULL DEFAULT FALSE,
    tested_at TIMESTAMP WITH TIME ZONE,
    test_result VARCHAR(10) NOT NULL DEFAULT 'UNTESTED',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE(organization_id, platform)
);

CREATE TABLE IF NOT EXISTS platform_visibility (
    platform VARCHAR(30) PRIMARY KEY,
    is_visible BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics_platform_config (
    platform VARCHAR(30) PRIMARY KEY,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
