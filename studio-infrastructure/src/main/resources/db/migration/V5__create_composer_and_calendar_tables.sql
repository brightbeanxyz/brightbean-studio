DROP TABLE IF EXISTS platform_post;
DROP TABLE IF EXISTS post;
DROP TABLE IF EXISTS publishing_queue;

CREATE TABLE IF NOT EXISTS composer_content_category (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, name)
);

CREATE TABLE IF NOT EXISTS composer_tag (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, name)
);

CREATE TABLE IF NOT EXISTS composer_idea_group (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS composer_idea (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    author_id UUID,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    media_asset_id UUID,
    status VARCHAR(20) NOT NULL DEFAULT 'UNASSIGNED',
    group_id UUID,
    position INT NOT NULL DEFAULT 0,
    post_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS composer_idea_media (
    id UUID PRIMARY KEY,
    idea_id UUID NOT NULL,
    media_asset_id UUID NOT NULL,
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(idea_id, media_asset_id)
);

CREATE TABLE IF NOT EXISTS composer_post (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    author_id UUID,
    title VARCHAR(255) NOT NULL DEFAULT '',
    caption TEXT NOT NULL DEFAULT '',
    first_comment TEXT NOT NULL DEFAULT '',
    internal_notes TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    category_id UUID,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS composer_platform_post (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    social_account_id UUID NOT NULL,
    platform_specific_title TEXT,
    platform_specific_caption TEXT,
    platform_specific_media TEXT,
    platform_specific_first_comment TEXT,
    platform_extra TEXT NOT NULL DEFAULT '{}',
    status VARCHAR(30) NOT NULL DEFAULT 'DRAFT',
    platform_post_id VARCHAR(255) NOT NULL DEFAULT '',
    publish_error TEXT NOT NULL DEFAULT '',
    published_at TIMESTAMP WITH TIME ZONE,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    retry_count INT NOT NULL DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(post_id, social_account_id)
);

CREATE TABLE IF NOT EXISTS composer_post_media (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    media_asset_id UUID NOT NULL,
    position INT NOT NULL DEFAULT 0,
    alt_text TEXT NOT NULL DEFAULT '',
    platform_overrides TEXT NOT NULL DEFAULT '{}',
    UNIQUE(post_id, media_asset_id)
);

CREATE TABLE IF NOT EXISTS composer_post_version (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL,
    version_number INT NOT NULL,
    snapshot TEXT NOT NULL,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(post_id, version_number)
);

CREATE TABLE IF NOT EXISTS composer_post_template (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    template_data TEXT NOT NULL DEFAULT '{}',
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS composer_csv_import_job (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    uploaded_by UUID,
    file_name VARCHAR(500) NOT NULL DEFAULT '',
    column_mapping TEXT NOT NULL DEFAULT '{}',
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    total_rows INT NOT NULL DEFAULT 0,
    processed_rows INT NOT NULL DEFAULT 0,
    result_summary TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS composer_feed (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(500) NOT NULL,
    website_url VARCHAR(500) NOT NULL DEFAULT '',
    added_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, url)
);

CREATE TABLE IF NOT EXISTS calendar_posting_slot (
    id UUID PRIMARY KEY,
    social_account_id UUID NOT NULL,
    day_of_week INT NOT NULL,
    time TIME NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(social_account_id, day_of_week, time)
);

CREATE TABLE IF NOT EXISTS calendar_queue (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    category_id UUID,
    social_account_id UUID NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calendar_queue_entry (
    id UUID PRIMARY KEY,
    queue_id UUID NOT NULL,
    post_id UUID NOT NULL,
    position INT NOT NULL DEFAULT 0,
    assigned_slot_datetime TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(queue_id, post_id)
);

CREATE TABLE IF NOT EXISTS calendar_recurrence_rule (
    id UUID PRIMARY KEY,
    post_id UUID NOT NULL UNIQUE,
    frequency VARCHAR(10) NOT NULL,
    interval_days INT NOT NULL DEFAULT 1,
    end_date DATE,
    last_generated_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS calendar_custom_event (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    color VARCHAR(7) NOT NULL DEFAULT '#3B82F6',
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_composer_post_workspace ON composer_post(workspace_id);
CREATE INDEX IF NOT EXISTS idx_composer_post_author ON composer_post(author_id);
CREATE INDEX IF NOT EXISTS idx_composer_post_scheduled ON composer_post(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_composer_platform_post_post ON composer_platform_post(post_id);
CREATE INDEX IF NOT EXISTS idx_composer_platform_post_account ON composer_platform_post(social_account_id);
CREATE INDEX IF NOT EXISTS idx_composer_platform_post_status ON composer_platform_post(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_composer_idea_workspace ON composer_idea(workspace_id);
CREATE INDEX IF NOT EXISTS idx_composer_idea_group ON composer_idea(group_id);
CREATE INDEX IF NOT EXISTS idx_composer_idea_status ON composer_idea(status);
CREATE INDEX IF NOT EXISTS idx_calendar_posting_slot_account ON calendar_posting_slot(social_account_id);
CREATE INDEX IF NOT EXISTS idx_calendar_queue_workspace ON calendar_queue(workspace_id);
CREATE INDEX IF NOT EXISTS idx_calendar_queue_entry_queue ON calendar_queue_entry(queue_id);
CREATE INDEX IF NOT EXISTS idx_calendar_custom_event_workspace ON calendar_custom_event(workspace_id);
CREATE INDEX IF NOT EXISTS idx_calendar_custom_event_dates ON calendar_custom_event(start_date, end_date);
