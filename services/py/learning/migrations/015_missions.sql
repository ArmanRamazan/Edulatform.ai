CREATE TABLE IF NOT EXISTS missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    concept_id UUID,
    mission_type VARCHAR(20) NOT NULL DEFAULT 'daily',
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    blueprint JSONB NOT NULL DEFAULT '{}',
    score FLOAT,
    mastery_delta FLOAT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_missions_user ON missions(user_id);
CREATE INDEX IF NOT EXISTS idx_missions_user_date ON missions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_missions_org ON missions(organization_id);
