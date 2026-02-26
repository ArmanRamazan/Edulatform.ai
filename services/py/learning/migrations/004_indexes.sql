-- quiz_attempts: separate student_id index for "all attempts by student" queries
CREATE INDEX IF NOT EXISTS idx_quiz_attempts_student_id ON quiz_attempts(student_id);

-- review_logs: reviewed_at for time-range analytics
CREATE INDEX IF NOT EXISTS idx_review_logs_reviewed_at ON review_logs(reviewed_at DESC);
