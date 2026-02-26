CREATE TABLE IF NOT EXISTS comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id       UUID NOT NULL,
    course_id       UUID NOT NULL,
    user_id         UUID NOT NULL,
    content         TEXT NOT NULL,
    parent_id       UUID REFERENCES comments(id) ON DELETE CASCADE,
    upvote_count    INT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_comments_lesson
    ON comments (lesson_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_comments_parent
    ON comments (parent_id)
    WHERE parent_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS comment_votes (
    comment_id  UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (comment_id, user_id)
);
