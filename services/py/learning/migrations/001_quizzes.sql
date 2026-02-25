CREATE TABLE IF NOT EXISTS quizzes (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id   UUID NOT NULL UNIQUE,
    course_id   UUID NOT NULL,
    teacher_id  UUID NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS questions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    text            TEXT NOT NULL,
    options         JSONB NOT NULL,
    correct_index   INT NOT NULL,
    explanation     TEXT,
    "order"         INT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id         UUID NOT NULL REFERENCES quizzes(id),
    student_id      UUID NOT NULL,
    answers         JSONB NOT NULL,
    score           FLOAT NOT NULL,
    completed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_questions_quiz_id ON questions(quiz_id);
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_quiz_student ON quiz_attempts(quiz_id, student_id);
