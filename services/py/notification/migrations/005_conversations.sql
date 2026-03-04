CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_1 UUID NOT NULL,
    participant_2 UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(participant_1, participant_2)
);

CREATE INDEX IF NOT EXISTS idx_conversations_p1
    ON conversations(participant_1, last_message_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_p2
    ON conversations(participant_2, last_message_at DESC);
