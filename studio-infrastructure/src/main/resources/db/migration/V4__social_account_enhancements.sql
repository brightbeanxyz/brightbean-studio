ALTER TABLE social_account ADD COLUMN connection_status VARCHAR(20) NOT NULL DEFAULT 'CONNECTED';
ALTER TABLE social_account ADD COLUMN last_health_check_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE social_account ADD COLUMN last_error TEXT;
ALTER TABLE social_account ADD COLUMN follower_count INT NOT NULL DEFAULT 0;
ALTER TABLE social_account ADD COLUMN instance_url VARCHAR(500);
ALTER TABLE social_account ADD COLUMN daily_post_limit_override INT;
ALTER TABLE social_account ADD COLUMN analytics_needs_reconnect BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX idx_social_account_status ON social_account(connection_status);
