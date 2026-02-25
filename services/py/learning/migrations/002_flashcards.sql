CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    concept TEXT NOT NULL,
    answer TEXT NOT NULL,
    source_type VARCHAR(20),
    source_id UUID,
    stability FLOAT DEFAULT 0,
    difficulty FLOAT DEFAULT 0,
    due TIMESTAMPTZ DEFAULT now(),
    last_review TIMESTAMPTZ,
    reps INT DEFAULT 0,
    lapses INT DEFAULT 0,
    state INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID REFERENCES flashcards(id) ON DELETE CASCADE,
    rating INT NOT NULL,
    review_duration_ms INT,
    reviewed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_flashcards_student_due ON flashcards(student_id, due);
CREATE INDEX IF NOT EXISTS idx_flashcards_student_course ON flashcards(student_id, course_id);
CREATE INDEX IF NOT EXISTS idx_review_logs_card ON review_logs(card_id);
