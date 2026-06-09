DROP TABLE IF EXISTS inbox_item;

CREATE TABLE IF NOT EXISTS inbox_message (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    platform_message_id VARCHAR NOT NULL,
    message_type VARCHAR NOT NULL,
    sender_name VARCHAR NOT NULL,
    sender_handle VARCHAR NOT NULL DEFAULT '',
    sender_avatar_url VARCHAR NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    sentiment VARCHAR NOT NULL DEFAULT '',
    sentiment_source VARCHAR NOT NULL DEFAULT '',
    status VARCHAR NOT NULL DEFAULT 'UNREAD',
    assigned_to UUID,
    parent_message_id UUID,
    related_post_id UUID,
    extra TEXT,
    received_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(social_account_id, platform_message_id)
);

CREATE TABLE IF NOT EXISTS inbox_reply (
    id UUID PRIMARY KEY,
    inbox_message_id UUID NOT NULL,
    author_id UUID,
    body TEXT NOT NULL,
    platform_reply_id VARCHAR NOT NULL DEFAULT '',
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS inbox_internal_note (
    id UUID PRIMARY KEY,
    inbox_message_id UUID NOT NULL,
    author_id UUID,
    body TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inbox_saved_reply (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    title VARCHAR NOT NULL,
    body TEXT NOT NULL,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS inbox_sla_config (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    target_response_minutes INT NOT NULL DEFAULT 60,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    auto_resolve_on_reply BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(workspace_id)
);

CREATE INDEX IF NOT EXISTS idx_inbox_message_workspace ON inbox_message(workspace_id, status);
CREATE INDEX IF NOT EXISTS idx_inbox_message_assigned ON inbox_message(assigned_to);
CREATE INDEX IF NOT EXISTS idx_inbox_reply_message ON inbox_reply(inbox_message_id);
CREATE INDEX IF NOT EXISTS idx_inbox_note_message ON inbox_internal_note(inbox_message_id);
CREATE INDEX IF NOT EXISTS idx_inbox_saved_reply_workspace ON inbox_saved_reply(workspace_id);

CREATE TABLE IF NOT EXISTS approvals_approval_action (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    platform_post_id UUID,
    user_id UUID,
    action VARCHAR NOT NULL,
    comment TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approvals_post_comment (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    author_id UUID,
    parent_comment_id UUID,
    body TEXT NOT NULL,
    visibility VARCHAR NOT NULL DEFAULT 'internal',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS approvals_approval_reminder (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    stage VARCHAR NOT NULL DEFAULT '',
    reminder_count INT NOT NULL DEFAULT 0,
    last_reminder_at TIMESTAMP WITH TIME ZONE,
    escalated BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(post_id)
);

CREATE INDEX IF NOT EXISTS idx_approval_action_post ON approvals_approval_action(post_id);
CREATE INDEX IF NOT EXISTS idx_post_comment_post ON approvals_post_comment(post_id);

CREATE TABLE IF NOT EXISTS notifications_notification (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    event_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    data TEXT,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications_preference (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    event_type VARCHAR NOT NULL,
    channel VARCHAR NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(user_id, event_type, channel)
);

CREATE TABLE IF NOT EXISTS notifications_delivery (
    id UUID PRIMARY KEY,
    notification_id UUID NOT NULL,
    channel VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'PENDING',
    error_message TEXT NOT NULL DEFAULT '',
    delivered_at TIMESTAMP WITH TIME ZONE,
    attempts INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications_quiet_hours (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    start_time TIME,
    end_time TIME,
    timezone VARCHAR NOT NULL DEFAULT 'UTC',
    digest_mode BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE(user_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_user ON notifications_notification(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notification_delivery_notification ON notifications_delivery(notification_id);
CREATE INDEX IF NOT EXISTS idx_notification_delivery_pending ON notifications_delivery(status) WHERE status = 'PENDING';

CREATE TABLE IF NOT EXISTS settings_org_setting (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    key VARCHAR NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, key)
);

CREATE TABLE IF NOT EXISTS settings_workspace_setting (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    key VARCHAR NOT NULL,
    value TEXT,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, key)
);

CREATE INDEX IF NOT EXISTS idx_org_setting_org ON settings_org_setting(organization_id);
CREATE INDEX IF NOT EXISTS idx_workspace_setting_workspace ON settings_workspace_setting(workspace_id);
