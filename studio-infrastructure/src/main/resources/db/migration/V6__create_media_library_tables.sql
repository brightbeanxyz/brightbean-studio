CREATE TABLE IF NOT EXISTS media_library_folder (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    workspace_id UUID,
    parent_folder_id UUID,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(workspace_id, parent_folder_id, name)
);

CREATE TABLE IF NOT EXISTS media_library_media_asset (
    id UUID PRIMARY KEY,
    organization_id UUID,
    workspace_id UUID,
    folder_id UUID,
    uploaded_by UUID,
    filename VARCHAR(255) NOT NULL,
    media_type VARCHAR(20) NOT NULL,
    mime_type VARCHAR(100) NOT NULL DEFAULT '',
    file_size BIGINT NOT NULL DEFAULT 0,
    width INT NOT NULL DEFAULT 0,
    height INT NOT NULL DEFAULT 0,
    duration DOUBLE PRECISION NOT NULL DEFAULT 0,
    file_path VARCHAR(1024) NOT NULL DEFAULT '',
    thumbnail_path VARCHAR(1024) NOT NULL DEFAULT '',
    alt_text TEXT NOT NULL DEFAULT '',
    title VARCHAR(255) NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    is_starred BOOLEAN NOT NULL DEFAULT FALSE,
    source VARCHAR(50) NOT NULL DEFAULT '',
    source_url VARCHAR(500) NOT NULL DEFAULT '',
    attribution TEXT NOT NULL DEFAULT '',
    processing_status VARCHAR(20) NOT NULL DEFAULT 'COMPLETED',
    processed_variants TEXT,
    current_version_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS media_library_asset_version (
    id UUID PRIMARY KEY,
    media_asset_id UUID NOT NULL,
    version_number INT NOT NULL,
    file_path VARCHAR(1024) NOT NULL DEFAULT '',
    thumbnail_path VARCHAR(1024) NOT NULL DEFAULT '',
    change_description VARCHAR(500) NOT NULL DEFAULT '',
    file_size BIGINT NOT NULL DEFAULT 0,
    width INT,
    height INT,
    duration DOUBLE PRECISION,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(media_asset_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_media_folder_workspace ON media_library_folder(workspace_id);
CREATE INDEX IF NOT EXISTS idx_media_asset_workspace ON media_library_media_asset(workspace_id, media_type, created_at);
CREATE INDEX IF NOT EXISTS idx_media_asset_starred ON media_library_media_asset(workspace_id, is_starred);
CREATE INDEX IF NOT EXISTS idx_media_asset_folder ON media_library_media_asset(folder_id);
CREATE INDEX IF NOT EXISTS idx_media_version_asset ON media_library_asset_version(media_asset_id);
