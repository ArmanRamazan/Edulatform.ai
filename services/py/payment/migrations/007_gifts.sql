CREATE TABLE IF NOT EXISTS gift_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID NOT NULL REFERENCES payments(id),
    gift_code VARCHAR(14) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'purchased'
        CHECK (status IN ('purchased', 'redeemed', 'expired')),
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    redeemed_at TIMESTAMPTZ,
    redeemed_by UUID,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_gift_code ON gift_purchases(gift_code);
CREATE INDEX IF NOT EXISTS idx_gift_buyer ON gift_purchases(buyer_id);
CREATE INDEX IF NOT EXISTS idx_gift_recipient ON gift_purchases(recipient_email);
