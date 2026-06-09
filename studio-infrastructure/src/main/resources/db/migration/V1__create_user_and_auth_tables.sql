CREATE TABLE IF NOT EXISTS accounts_user (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    avatar VARCHAR(1024),
    totp_secret VARCHAR(255),
    totp_recovery_codes TEXT,
    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    last_workspace_id UUID,
    tos_accepted_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts_oauth_connection (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_user_id)
);

CREATE TABLE IF NOT EXISTS accounts_session (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES accounts_user(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    device_info TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_email ON accounts_user(email);
CREATE INDEX IF NOT EXISTS idx_accounts_session_token_hash ON accounts_session(token_hash);
CREATE INDEX IF NOT EXISTS idx_accounts_session_user_id ON accounts_session(user_id);
CREATE INDEX IF NOT EXISTS idx_accounts_oauth_user_provider ON accounts_oauth_connection(user_id, provider);
