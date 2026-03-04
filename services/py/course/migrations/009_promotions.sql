CREATE TABLE IF NOT EXISTS course_promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    original_price DECIMAL(10,2) NOT NULL,
    promo_price DECIMAL(10,2) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (promo_price < original_price),
    CHECK (ends_at > starts_at)
);

CREATE INDEX IF NOT EXISTS idx_promotions_course ON course_promotions(course_id);
CREATE INDEX IF NOT EXISTS idx_promotions_active ON course_promotions(is_active, starts_at, ends_at);
