CREATE TABLE IF NOT EXISTS streaks (
    user_id             UUID PRIMARY KEY,
    current_streak      INT NOT NULL DEFAULT 1,
    longest_streak      INT NOT NULL DEFAULT 1,
    last_activity_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
