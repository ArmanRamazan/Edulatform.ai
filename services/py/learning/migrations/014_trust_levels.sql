CREATE TABLE IF NOT EXISTS trust_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    organization_id UUID NOT NULL,
    level INT NOT NULL DEFAULT 0,
    total_missions_completed INT NOT NULL DEFAULT 0,
    total_concepts_mastered INT NOT NULL DEFAULT 0,
    unlocked_areas JSONB DEFAULT '[]',
    level_up_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trust_levels_user ON trust_levels(user_id);
CREATE INDEX IF NOT EXISTS idx_trust_levels_org ON trust_levels(organization_id);
