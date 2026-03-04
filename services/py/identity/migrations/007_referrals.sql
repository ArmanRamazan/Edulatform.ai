-- Add referral_code column to users
ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(12) UNIQUE;

-- Generate referral codes for existing users that don't have one
DO $$
DECLARE
    r RECORD;
    new_code VARCHAR(12);
    chars TEXT := 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    i INT;
BEGIN
    FOR r IN SELECT id FROM users WHERE referral_code IS NULL LOOP
        LOOP
            new_code := 'REF-';
            FOR i IN 1..8 LOOP
                new_code := new_code || substr(chars, floor(random() * 36 + 1)::int, 1);
            END LOOP;
            BEGIN
                UPDATE users SET referral_code = new_code WHERE id = r.id;
                EXIT;
            EXCEPTION WHEN unique_violation THEN
                -- retry with a different code
            END;
        END LOOP;
    END LOOP;
END $$;

-- Create referrals table
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL REFERENCES users(id),
    referee_id UUID NOT NULL REFERENCES users(id) UNIQUE,
    referral_code VARCHAR(12) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'completed', 'expired')),
    reward_type VARCHAR(20),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id);
