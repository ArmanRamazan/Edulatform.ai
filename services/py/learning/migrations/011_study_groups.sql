CREATE TABLE IF NOT EXISTS study_groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    creator_id  UUID NOT NULL,
    max_members INT NOT NULL DEFAULT 10,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_study_groups_course ON study_groups(course_id);

CREATE TABLE IF NOT EXISTS study_group_members (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id  UUID NOT NULL REFERENCES study_groups(id) ON DELETE CASCADE,
    user_id   UUID NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_sgm_group ON study_group_members(group_id);
CREATE INDEX IF NOT EXISTS idx_sgm_user ON study_group_members(user_id);
