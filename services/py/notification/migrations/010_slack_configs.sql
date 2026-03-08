CREATE TABLE IF NOT EXISTS slack_configs (
    org_id UUID PRIMARY KEY,
    webhook_url TEXT NOT NULL,
    channel TEXT NOT NULL DEFAULT '#engineering',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
