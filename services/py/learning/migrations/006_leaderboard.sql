CREATE TABLE IF NOT EXISTS leaderboard_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    score INT NOT NULL DEFAULT 0,
    opted_in BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(student_id, course_id)
);

CREATE INDEX IF NOT EXISTS idx_leaderboard_course_score
    ON leaderboard_entries (course_id, score DESC)
    WHERE opted_in = TRUE;
