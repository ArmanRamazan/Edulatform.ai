CREATE TABLE IF NOT EXISTS teacher_earnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID NOT NULL UNIQUE,
    gross_amount DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,4) NOT NULL DEFAULT 0.3000,
    net_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    stripe_transfer_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_teacher_earnings_teacher_id ON teacher_earnings(teacher_id);
CREATE INDEX IF NOT EXISTS idx_payouts_teacher_id ON payouts(teacher_id);
