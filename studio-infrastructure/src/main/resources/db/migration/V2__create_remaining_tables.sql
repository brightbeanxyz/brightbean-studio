CREATE TABLE IF NOT EXISTS publishing_queue (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    post_id UUID NOT NULL,
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    attempts INT NOT NULL DEFAULT 0,
    last_attempt_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS platform_post (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    platform_post_id VARCHAR(255),
    platform_url VARCHAR(1024),
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    error_message TEXT,
    published_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS inbox_item (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    platform_type VARCHAR(30) NOT NULL,
    platform_item_id VARCHAR(255) NOT NULL,
    type VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    author_avatar_url VARCHAR(1024),
    media_urls TEXT,
    sentiment VARCHAR(10),
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    platform_created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS approval_request (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    post_id UUID NOT NULL,
    requested_by UUID NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    reviewed_by UUID,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS idx_publishing_queue_status ON publishing_queue(status);
CREATE INDEX IF NOT EXISTS idx_publishing_queue_workspace ON publishing_queue(workspace_id);
CREATE INDEX IF NOT EXISTS idx_platform_post_post_id ON platform_post(post_id);
CREATE INDEX IF NOT EXISTS idx_platform_post_account ON platform_post(social_account_id);
CREATE INDEX IF NOT EXISTS idx_inbox_item_workspace ON inbox_item(workspace_id);
CREATE INDEX IF NOT EXISTS idx_inbox_item_account ON inbox_item(social_account_id);
CREATE INDEX IF NOT EXISTS idx_approval_request_workspace ON approval_request(workspace_id);
CREATE INDEX IF NOT EXISTS idx_approval_request_post ON approval_request(post_id);
