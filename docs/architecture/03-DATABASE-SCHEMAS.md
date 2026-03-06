# 03 — Database Schemas

> Последнее обновление: 2026-03-06

Каждый сервис владеет своей БД (PostgreSQL 16). Миграции: идемпотентные SQL файлы, forward-only.

---

## Identity DB (`identity-db:5433`)

### users
```sql
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    referral_code VARCHAR(20) UNIQUE,
    role VARCHAR(20) DEFAULT 'student',        -- student | teacher | admin
    is_verified BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    is_public BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### organizations
```sql
CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    logo_url TEXT,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### org_members
```sql
CREATE TABLE IF NOT EXISTS org_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL,
    role VARCHAR(20) DEFAULT 'member',        -- owner | admin | member
    joined_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (organization_id, user_id)
);
```

### refresh_tokens / email_verifications / password_resets
```sql
-- Все три таблицы имеют одинаковую структуру:
token VARCHAR PRIMARY KEY,
user_id UUID NOT NULL,
expires_at TIMESTAMPTZ NOT NULL
```

### follows
```sql
CREATE TABLE IF NOT EXISTS follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL,
    following_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (follower_id, following_id)
);
```

### referrals
```sql
CREATE TABLE IF NOT EXISTS referrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id UUID NOT NULL,
    referee_id UUID NOT NULL,
    referral_code VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- pending | completed | expired
    reward_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

---

## Course DB (`course-db:5434`)

### courses
```sql
CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    is_free BOOLEAN DEFAULT FALSE,
    price NUMERIC(10,2) DEFAULT 0,
    duration_minutes INT DEFAULT 0,
    level VARCHAR(20) DEFAULT 'beginner',     -- beginner | intermediate | advanced
    category_id UUID REFERENCES categories(id),
    avg_rating NUMERIC(3,2) DEFAULT 0,
    review_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- Indexes: teacher_id, category_id, full-text (title, description)
```

### modules
```sql
CREATE TABLE IF NOT EXISTS modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    "order" INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### lessons
```sql
CREATE TABLE IF NOT EXISTS lessons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    video_url TEXT,
    duration_minutes INT DEFAULT 0,
    "order" INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### reviews
```sql
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    rating INT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, course_id)
);
```

### categories
```sql
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL
);
```

### course_bundles / bundle_courses
```sql
CREATE TABLE IF NOT EXISTS course_bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL,
    discount_percent INT DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS bundle_courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bundle_id UUID NOT NULL REFERENCES course_bundles(id) ON DELETE CASCADE,
    course_id UUID NOT NULL,
    UNIQUE (bundle_id, course_id)
);
```

### course_promotions
```sql
CREATE TABLE IF NOT EXISTS course_promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    original_price NUMERIC(10,2) NOT NULL,
    promo_price NUMERIC(10,2) NOT NULL,
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### wishlist
```sql
CREATE TABLE IF NOT EXISTS wishlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    course_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, course_id)
);
```

---

## Enrollment DB (`enrollment-db:5435`)

### enrollments
```sql
CREATE TABLE IF NOT EXISTS enrollments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID,
    status VARCHAR(20) DEFAULT 'active',      -- active | completed | cancelled
    enrolled_at TIMESTAMPTZ DEFAULT now(),
    total_lessons INT DEFAULT 0,
    UNIQUE (student_id, course_id)
);
```

### lesson_progress
```sql
CREATE TABLE IF NOT EXISTS lesson_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enrollment_id UUID NOT NULL REFERENCES enrollments(id),
    lesson_id UUID NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (enrollment_id, lesson_id)
);
```

---

## Payment DB (`payment-db:5436`)

### payments
```sql
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- pending | completed | failed | refunded
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### subscription_plans
```sql
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,         -- free | student | pro
    stripe_price_id VARCHAR(255),
    price_monthly NUMERIC(10,2) DEFAULT 0,
    price_yearly NUMERIC(10,2) DEFAULT 0,
    ai_credits_daily INT DEFAULT 0,
    features JSONB DEFAULT '{}'
);
```

### user_subscriptions
```sql
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE
);
```

### teacher_earnings / payouts
```sql
CREATE TABLE IF NOT EXISTS teacher_earnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    gross_amount NUMERIC(10,2) NOT NULL,
    commission_rate NUMERIC(5,4) NOT NULL,
    net_amount NUMERIC(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    stripe_transfer_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    requested_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

### coupons / coupon_usages
```sql
CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    discount_type VARCHAR(20) NOT NULL,       -- percentage | fixed
    discount_value NUMERIC(10,2) NOT NULL,
    max_uses INT,
    current_uses INT DEFAULT 0,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    course_id UUID,
    created_by UUID NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS coupon_usages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID NOT NULL REFERENCES coupons(id),
    user_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    used_at TIMESTAMPTZ DEFAULT now()
);
```

### refunds
```sql
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL,
    user_id UUID NOT NULL,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending',     -- pending | approved | rejected
    amount NUMERIC(10,2) NOT NULL,
    admin_note TEXT,
    requested_at TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);
```

### gifts
```sql
CREATE TABLE IF NOT EXISTS gifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID,
    gift_code VARCHAR(20) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',     -- pending | redeemed | expired
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    redeemed_at TIMESTAMPTZ,
    redeemed_by UUID,
    expires_at TIMESTAMPTZ
);
```

### org_subscriptions
```sql
CREATE TABLE IF NOT EXISTS org_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID UNIQUE NOT NULL,
    plan_tier VARCHAR(20) NOT NULL,           -- pilot | starter | growth | enterprise
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    max_seats INT DEFAULT 5,
    current_seats INT DEFAULT 0,
    price_cents INT NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    trial_ends_at TIMESTAMPTZ,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Notification DB (`notification-db:5437`)

### notifications
```sql
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    type VARCHAR(50) NOT NULL,                -- enrollment | payment | review | streak_reminder | flashcard_reminder | system
    title VARCHAR(255) NOT NULL,
    body TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- Index: user_id, created_at DESC
```

### conversations / messages
```sql
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_1 UUID NOT NULL,
    participant_2 UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_message_at TIMESTAMPTZ,
    UNIQUE (participant_1, participant_2)
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    sender_id UUID NOT NULL,
    content TEXT NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### email_sent_log
```sql
CREATE TABLE IF NOT EXISTS email_sent_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_id UUID REFERENCES notifications(id),
    user_id UUID NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT now()
);
```

---

## Learning DB (`learning-db:5438`)

### quizzes / questions / quiz_attempts
```sql
CREATE TABLE IF NOT EXISTS quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID UNIQUE NOT NULL,
    course_id UUID NOT NULL,
    teacher_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_index INT NOT NULL,
    explanation TEXT,
    "order" INT NOT NULL
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID NOT NULL REFERENCES quizzes(id),
    student_id UUID NOT NULL,
    answers JSONB NOT NULL,
    score NUMERIC(5,2) NOT NULL,
    completed_at TIMESTAMPTZ DEFAULT now()
);
```

### flashcards (FSRS) / review_logs
```sql
CREATE TABLE IF NOT EXISTS flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID,
    concept VARCHAR(500) NOT NULL,
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
-- Index: student_id, due

CREATE TABLE IF NOT EXISTS review_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    rating INT NOT NULL,
    review_duration_ms INT,
    reviewed_at TIMESTAMPTZ DEFAULT now()
);
```

### concepts / concept_prerequisites / concept_mastery
```sql
CREATE TABLE IF NOT EXISTS concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    lesson_id UUID,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    parent_id UUID REFERENCES concepts(id),
    "order" INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS concept_prerequisites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    prerequisite_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE (concept_id, prerequisite_id)
);

CREATE TABLE IF NOT EXISTS concept_mastery (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES concepts(id),
    mastery NUMERIC(3,2) DEFAULT 0 CHECK (mastery BETWEEN 0 AND 1),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, concept_id)
);
```

### streaks / xp_points / badges / user_badges
```sql
CREATE TABLE IF NOT EXISTS streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID,
    current_count INT DEFAULT 0,
    best_count INT DEFAULT 0,
    last_activity_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS xp_points (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID,
    points INT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon_url TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS user_badges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    badge_id UUID NOT NULL REFERENCES badges(id),
    earned_at TIMESTAMPTZ DEFAULT now()
);
```

### discussions / discussion_upvotes
```sql
CREATE TABLE IF NOT EXISTS discussions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id UUID NOT NULL,
    student_id UUID NOT NULL,
    parent_id UUID REFERENCES discussions(id),
    content TEXT NOT NULL,
    upvote_count INT DEFAULT 0,
    pinned BOOLEAN DEFAULT FALSE,
    flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS discussion_upvotes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    UNIQUE (comment_id, user_id)
);
```

### study_groups / group_members
```sql
CREATE TABLE IF NOT EXISTS study_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES study_groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    joined_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (group_id, user_id)
);
```

### certificates / pretests / leaderboards / trust_levels / missions / activity_feed / velocity
```sql
CREATE TABLE IF NOT EXISTS certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID NOT NULL,
    issue_date TIMESTAMPTZ DEFAULT now(),
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pretests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    student_id UUID NOT NULL,
    total_questions INT DEFAULT 0,
    correct_answers INT DEFAULT 0,
    skipped_count INT DEFAULT 0,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS leaderboards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id UUID NOT NULL,
    student_id UUID NOT NULL,
    score NUMERIC(10,2) DEFAULT 0,
    rank INT,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (course_id, student_id)
);

CREATE TABLE IF NOT EXISTS trust_levels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    level INT DEFAULT 1 CHECK (level BETWEEN 1 AND 5),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (student_id, organization_id)
);

CREATE TABLE IF NOT EXISTS missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    organization_id UUID,
    concept_id UUID,
    mission_type VARCHAR(20) DEFAULT 'daily',
    status VARCHAR(20) DEFAULT 'created',     -- created | in_progress | completed
    blueprint JSONB DEFAULT '{}',
    score NUMERIC(5,2),
    mastery_delta NUMERIC(3,2),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS activity_feed (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    subject_id UUID,
    created_at TIMESTAMPTZ DEFAULT now()
);
-- Index: user_id, created_at DESC

CREATE TABLE IF NOT EXISTS velocity (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id UUID,
    lessons_per_week NUMERIC(5,2) DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT now()
);
```

---

## RAG DB (`rag-db:5439`)

### documents
```sql
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    source_type VARCHAR(20) NOT NULL,         -- file | github | url | text
    source_path TEXT,
    title VARCHAR(500),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

### chunks (pgvector)
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    chunk_index INT NOT NULL,
    embedding vector(768),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
-- Index: ivfflat on embedding for ANN search
```

### org_concepts / concept_relationships
```sql
CREATE TABLE IF NOT EXISTS org_concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    source_document_id UUID REFERENCES documents(id),
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS concept_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id UUID NOT NULL REFERENCES org_concepts(id) ON DELETE CASCADE,
    related_concept_id UUID NOT NULL REFERENCES org_concepts(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50),
    UNIQUE (concept_id, related_concept_id)
);
```
