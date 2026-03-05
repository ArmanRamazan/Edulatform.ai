CREATE TABLE IF NOT EXISTS org_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL UNIQUE,
    plan_tier VARCHAR(20) NOT NULL DEFAULT 'pilot',
    stripe_subscription_id VARCHAR(200),
    stripe_customer_id VARCHAR(200),
    max_seats INT NOT NULL DEFAULT 20,
    current_seats INT NOT NULL DEFAULT 0,
    price_cents INT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_org_subscriptions_stripe_sub_id
    ON org_subscriptions (stripe_subscription_id)
    WHERE stripe_subscription_id IS NOT NULL;
