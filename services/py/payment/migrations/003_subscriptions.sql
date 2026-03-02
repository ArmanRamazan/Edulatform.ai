CREATE TABLE IF NOT EXISTS subscription_plans (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(50) NOT NULL UNIQUE,
    stripe_price_id  VARCHAR(255),
    price_monthly    DECIMAL(10,2) NOT NULL,
    price_yearly     DECIMAL(10,2),
    ai_credits_daily INT NOT NULL,
    features         JSONB NOT NULL DEFAULT '{}',
    created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_subscriptions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                UUID NOT NULL UNIQUE,
    plan_id                UUID NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id     VARCHAR(255),
    status                 VARCHAR(20) NOT NULL DEFAULT 'active',
    current_period_start   TIMESTAMPTZ,
    current_period_end     TIMESTAMPTZ,
    cancel_at_period_end   BOOLEAN DEFAULT false,
    created_at             TIMESTAMPTZ DEFAULT now(),
    updated_at             TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user
    ON user_subscriptions(user_id);

CREATE INDEX IF NOT EXISTS idx_user_subscriptions_stripe
    ON user_subscriptions(stripe_subscription_id);

-- Seed default plans (idempotent)
INSERT INTO subscription_plans (name, price_monthly, price_yearly, ai_credits_daily, features)
VALUES
    ('free', 0.00, NULL, 10, '{"courses": true, "ai_features": "limited"}'),
    ('student', 9.99, 99.99, 100, '{"courses": true, "ai_features": "standard"}'),
    ('pro', 19.99, 199.99, -1, '{"courses": true, "ai_features": "unlimited", "offline": true}')
ON CONFLICT (name) DO NOTHING;
