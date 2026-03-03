CREATE TABLE IF NOT EXISTS pretests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    course_id UUID NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    UNIQUE(user_id, course_id)
);

CREATE TABLE IF NOT EXISTS pretest_answers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pretest_id UUID NOT NULL REFERENCES pretests(id) ON DELETE CASCADE,
    concept_id UUID NOT NULL,
    question TEXT NOT NULL,
    user_answer TEXT,
    correct_answer TEXT NOT NULL,
    is_correct BOOLEAN,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pretests_user_course ON pretests(user_id, course_id);
CREATE INDEX IF NOT EXISTS idx_pretest_answers_pretest ON pretest_answers(pretest_id);
