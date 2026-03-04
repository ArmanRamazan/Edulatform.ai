# 03 — Database Schemas

> Последнее обновление: 2026-03-05
> Стадия: B2B Agentic Adaptive Learning Pivot

---

## Принцип: Database-per-Service

Каждый сервис владеет собственной PostgreSQL базой. Прямой доступ к БД другого сервиса запрещён. AI Service не имеет собственной БД (stateless, только Redis).

```
identity-db (PostgreSQL 16 Alpine, :5433)
  └── database: identity
       ├── table: users
       ├── table: refresh_tokens
       ├── table: email_verification_tokens
       ├── table: password_reset_tokens
       ├── table: referrals
       ├── table: follows
       ├── table: organizations          (NEW)
       └── table: org_members            (NEW)

payment-db (PostgreSQL 16 Alpine, :5436)
  └── database: payment
       ├── table: payments
       ├── table: subscription_plans
       ├── table: user_subscriptions
       ├── table: teacher_earnings
       ├── table: payouts
       ├── table: coupons
       ├── table: coupon_usages
       ├── table: refunds
       ├── table: gift_purchases
       └── table: org_subscriptions      (NEW)

notification-db (PostgreSQL 16 Alpine, :5437)
  └── database: notification
       ├── table: notifications
       ├── table: conversations
       └── table: messages

learning-db (PostgreSQL 16 Alpine, :5438)
  └── database: learning
       ├── table: quizzes
       ├── table: questions
       ├── table: quiz_attempts
       ├── table: flashcards
       ├── table: review_logs
       ├── table: concepts
       ├── table: concept_prerequisites
       ├── table: concept_mastery
       ├── table: streaks
       ├── table: leaderboard_scores
       ├── table: comments
       ├── table: comment_upvotes
       ├── table: xp_ledger
       ├── table: badges
       ├── table: pretests
       ├── table: pretest_answers
       ├── table: activity_feed
       ├── table: study_groups
       ├── table: study_group_members
       ├── table: certificates
       ├── table: missions               (NEW)
       └── table: trust_levels           (NEW)

rag-db (PostgreSQL 16 Alpine + pgvector, :5439)     (NEW)
  └── database: rag
       ├── table: documents              (NEW)
       ├── table: chunks                 (NEW, pgvector)
       ├── table: org_concepts           (NEW)
       ├── table: concept_relationships  (NEW)
       ├── table: onboarding_templates   (NEW)
       └── table: template_stages        (NEW)

--- DORMANT ---

course-db (PostgreSQL 16 Alpine, :5434) — dormant
  └── database: course
       ├── table: categories
       ├── table: courses
       ├── table: modules
       ├── table: lessons
       ├── table: reviews
       ├── table: course_bundles
       ├── table: bundle_courses
       ├── table: course_promotions
       └── table: wishlist

enrollment-db (PostgreSQL 16 Alpine, :5435) — dormant
  └── database: enrollment
       ├── table: enrollments
       └── table: lesson_progress
```

**Итого (активные): 48 таблиц в 5 базах данных. Dormant: 11 таблиц в 2 базах.**

---

## Identity DB

### ENUM: `user_role`

```sql
CREATE TYPE user_role AS ENUM ('student', 'teacher', 'admin');
```

### Table: `users`

```sql
CREATE TABLE IF NOT EXISTS users (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email          VARCHAR(255) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    name           VARCHAR(255) NOT NULL,
    role           user_role NOT NULL DEFAULT 'student',
    is_verified    BOOLEAN NOT NULL DEFAULT false,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    referral_code  VARCHAR(12) UNIQUE,
    bio            TEXT,
    avatar_url     VARCHAR(2000),
    is_public      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Email для входа |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt hash пароля |
| `name` | VARCHAR(255) | NOT NULL | Имя пользователя |
| `role` | user_role | NOT NULL, DEFAULT 'student' | Роль: student, teacher или admin |
| `is_verified` | BOOLEAN | NOT NULL, DEFAULT false | Верификация преподавателя (admin only) |
| `email_verified` | BOOLEAN | NOT NULL, DEFAULT false | Подтверждение email |
| `referral_code` | VARCHAR(12) | UNIQUE | Реферальный код (REF-XXXXXXXX), генерируется при регистрации |
| `bio` | TEXT | nullable | Биография пользователя |
| `avatar_url` | VARCHAR(2000) | nullable | URL аватара |
| `is_public` | BOOLEAN | NOT NULL, DEFAULT true | Видимость публичного профиля |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (email) + UNIQUE (referral_code).

---

### Table: `refresh_tokens`

```sql
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    family_id  UUID NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | FK → users(id) CASCADE, NOT NULL | Владелец токена |
| `token_hash` | VARCHAR(255) | UNIQUE, NOT NULL | SHA-256 хэш refresh token |
| `family_id` | UUID | NOT NULL | Группа токенов (для reuse detection) |
| `is_revoked` | BOOLEAN | NOT NULL, DEFAULT false | Отозван ли токен |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Время истечения (TTL 30 дней) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (token_hash) + idx_refresh_tokens_user_id + idx_refresh_tokens_family_id.

**Token rotation:** при каждом refresh все токены в family отзываются, создаётся новый с тем же family_id. При повторном использовании отозванного токена — вся family блокируется.

---

### Table: `email_verification_tokens`

```sql
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Индексы:** PK (id) + UNIQUE (token_hash) + idx_email_verify_user_id.

TTL: 24 часа. При регистрации создаётся токен; raw token логируется `[EMAIL_VERIFY]` (stub).

---

### Table: `password_reset_tokens`

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Индексы:** PK (id) + UNIQUE (token_hash) + idx_password_reset_user_id.

TTL: 1 час. Rate limit: 3 запроса в час на пользователя. После сброса пароля все refresh tokens отзываются.

---

### Table: `referrals`

```sql
CREATE TABLE IF NOT EXISTS referrals (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    referrer_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referee_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referral_code VARCHAR(12) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'pending',
    reward_type   VARCHAR(50),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ
);
```

**Индексы:** PK (id) + idx_referrals_referrer_id + idx_referrals_referee_id.

---

### Table: `follows`

```sql
CREATE TABLE IF NOT EXISTS follows (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id  UUID NOT NULL REFERENCES users(id),
    following_id UUID NOT NULL REFERENCES users(id),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(follower_id, following_id)
);
```

**Индексы:** PK (id) + idx_follows_follower + idx_follows_following + UNIQUE(follower_id, following_id).

---

### Table: `organizations` (NEW)

```sql
CREATE TABLE IF NOT EXISTS organizations (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(255) NOT NULL,
    slug       VARCHAR(100) NOT NULL UNIQUE,
    domain     VARCHAR(255) UNIQUE,
    owner_id   UUID NOT NULL REFERENCES users(id),
    logo_url   VARCHAR(2000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор организации |
| `name` | VARCHAR(255) | NOT NULL | Название организации |
| `slug` | VARCHAR(100) | UNIQUE, NOT NULL | URL-friendly slug |
| `domain` | VARCHAR(255) | UNIQUE, nullable | Корпоративный домен (для auto-join) |
| `owner_id` | UUID | FK → users(id), NOT NULL | Создатель/владелец организации |
| `logo_url` | VARCHAR(2000) | nullable | URL логотипа |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата обновления |

**Индексы:** PK (id) + UNIQUE (slug) + UNIQUE (domain) + idx_org_owner_id.

---

### Table: `org_members` (NEW)

```sql
CREATE TABLE IF NOT EXISTS org_members (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL DEFAULT 'member',
    joined_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(organization_id, user_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `organization_id` | UUID | FK → organizations(id) CASCADE, NOT NULL | Организация |
| `user_id` | UUID | FK → users(id) CASCADE, NOT NULL | Пользователь |
| `role` | VARCHAR(20) | NOT NULL, DEFAULT 'member' | Роль в организации: `owner`, `admin`, `member` |
| `joined_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата вступления |

**Индексы:** PK (id) + UNIQUE(organization_id, user_id) + idx_org_members_user_id + idx_org_members_org_id.

**Миграции (Identity):**
- `001_users.sql` — создание таблицы users
- `002_add_role.sql` — добавление role ENUM и is_verified
- `003_add_admin_role.sql` — добавление значения `admin` в ENUM user_role
- `004_refresh_tokens.sql` — таблица refresh_tokens + индексы
- `005_email_verification.sql` — email_verified column + email_verification_tokens table
- `006_password_reset.sql` — password_reset_tokens table
- `007_referrals.sql` — referral_code column в users + таблица referrals
- `008_add_is_public.sql` — is_public column для управления видимостью профиля
- `009_follows.sql` — таблица follows
- `010_organizations.sql` — таблица organizations (NEW)
- `011_org_members.sql` — таблица org_members (NEW)

---

## Payment DB

### Table: `payments`

```sql
CREATE TABLE IF NOT EXISTS payments (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id  UUID NOT NULL,
    amount     NUMERIC(12,2) NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'pending',
    coupon_code VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `student_id` | UUID | NOT NULL | Плательщик |
| `course_id` | UUID | NOT NULL | Оплачиваемый курс |
| `amount` | NUMERIC(12,2) | NOT NULL | Сумма |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Статус: pending, completed, refunded |
| `coupon_code` | VARCHAR(50) | nullable | Применённый купон |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_payments_student_id + idx_payments_course_id.

---

### Table: `subscription_plans`

```sql
CREATE TABLE IF NOT EXISTS subscription_plans (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name           VARCHAR(100) NOT NULL UNIQUE,
    price_monthly  NUMERIC(10,2) NOT NULL,
    price_yearly   NUMERIC(10,2) NOT NULL,
    features       JSONB NOT NULL DEFAULT '{}',
    stripe_price_id_monthly VARCHAR(255),
    stripe_price_id_yearly  VARCHAR(255),
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `user_subscriptions`

```sql
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              UUID NOT NULL,
    plan_id              UUID NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id   VARCHAR(255),
    status               VARCHAR(20) NOT NULL DEFAULT 'active',
    billing_period       VARCHAR(10) NOT NULL DEFAULT 'monthly',
    current_period_start TIMESTAMPTZ NOT NULL,
    current_period_end   TIMESTAMPTZ NOT NULL,
    cancelled_at         TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `teacher_earnings`

```sql
CREATE TABLE IF NOT EXISTS teacher_earnings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id  UUID NOT NULL,
    payment_id  UUID NOT NULL REFERENCES payments(id),
    course_id   UUID NOT NULL,
    amount      NUMERIC(12,2) NOT NULL,
    commission  NUMERIC(12,2) NOT NULL,
    net_amount  NUMERIC(12,2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `payouts`

```sql
CREATE TABLE IF NOT EXISTS payouts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id  UUID NOT NULL,
    amount      NUMERIC(12,2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    method      VARCHAR(50) NOT NULL DEFAULT 'bank_transfer',
    processed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `coupons`

```sql
CREATE TABLE IF NOT EXISTS coupons (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code             VARCHAR(50) NOT NULL UNIQUE,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 100),
    max_uses         INTEGER,
    current_uses     INTEGER NOT NULL DEFAULT 0,
    created_by       UUID NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT true,
    expires_at       TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `coupon_usages`

```sql
CREATE TABLE IF NOT EXISTS coupon_usages (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id  UUID NOT NULL REFERENCES coupons(id),
    user_id    UUID NOT NULL,
    payment_id UUID NOT NULL REFERENCES payments(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(coupon_id, user_id)
);
```

---

### Table: `refunds`

```sql
CREATE TABLE IF NOT EXISTS refunds (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id  UUID NOT NULL REFERENCES payments(id),
    user_id     UUID NOT NULL,
    reason      TEXT NOT NULL DEFAULT '',
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(payment_id)
);
```

14-дневное окно для запроса возврата. Один возврат на платёж. При approve → payment.status = 'refunded'.

---

### Table: `gift_purchases`

```sql
CREATE TABLE IF NOT EXISTS gift_purchases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id        UUID NOT NULL,
    course_id       UUID NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    gift_code       VARCHAR(20) NOT NULL UNIQUE,
    message         TEXT,
    status          VARCHAR(20) NOT NULL DEFAULT 'purchased',
    amount          NUMERIC(12,2) NOT NULL,
    redeemed_by     UUID,
    redeemed_at     TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Status: `purchased`, `redeemed`, `expired`. Expires 30 days after purchase.

---

### Table: `org_subscriptions` (NEW)

```sql
CREATE TABLE IF NOT EXISTS org_subscriptions (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id        UUID NOT NULL,
    plan                   VARCHAR(50) NOT NULL,
    seats                  INTEGER NOT NULL,
    status                 VARCHAR(20) NOT NULL DEFAULT 'active',
    billing_period         VARCHAR(10) NOT NULL DEFAULT 'monthly',
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id     VARCHAR(255),
    current_period_start   TIMESTAMPTZ NOT NULL,
    current_period_end     TIMESTAMPTZ NOT NULL,
    cancelled_at           TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `organization_id` | UUID | NOT NULL | ID организации (из Identity) |
| `plan` | VARCHAR(50) | NOT NULL | План: `team`, `enterprise` |
| `seats` | INTEGER | NOT NULL | Количество мест |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'active' | Статус: active, cancelled, past_due |
| `billing_period` | VARCHAR(10) | NOT NULL, DEFAULT 'monthly' | monthly или yearly |
| `stripe_subscription_id` | VARCHAR(255) | nullable | Stripe subscription ID |
| `stripe_customer_id` | VARCHAR(255) | nullable | Stripe customer ID |
| `current_period_start` | TIMESTAMPTZ | NOT NULL | Начало текущего периода |
| `current_period_end` | TIMESTAMPTZ | NOT NULL | Конец текущего периода |
| `cancelled_at` | TIMESTAMPTZ | nullable | Дата отмены |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата обновления |

**Индексы:** PK (id) + idx_org_sub_org_id (organization_id) + idx_org_sub_status.

**Миграции (Payment):**
- `001_payments.sql` — таблица payments
- `002_indexes.sql` — FK indexes
- `003_subscription_plans.sql` — subscription_plans + user_subscriptions
- `004_teacher_earnings.sql` — teacher_earnings + payouts
- `005_coupons.sql` — coupons + coupon_usages
- `006_refunds.sql` — таблица refunds
- `007_gifts.sql` — таблица gift_purchases
- `008_org_subscriptions.sql` — таблица org_subscriptions (NEW)

---

## Notification DB

### Table: `notifications`

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    type       VARCHAR(50) NOT NULL,
    title      VARCHAR(500) NOT NULL,
    message    TEXT NOT NULL DEFAULT '',
    is_read    BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Индексы:** PK (id) + idx_notifications_user_id + idx_notifications_unread (user_id, is_read).

---

### Table: `conversations`

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_1   UUID NOT NULL,
    participant_2   UUID NOT NULL,
    last_message_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(participant_1, participant_2)
);
```

Participant validation: participant_1 < participant_2 (canonical ordering).

**Индексы:** PK (id) + UNIQUE(participant_1, participant_2) + idx_conv_p1 + idx_conv_p2.

---

### Table: `messages`

```sql
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    sender_id       UUID NOT NULL,
    content         VARCHAR(2000) NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Лимит: 1–2000 символов.

**Индексы:** PK (id) + idx_messages_conversation_id + idx_messages_sender_id.

**Миграции (Notification):**
- `001_notifications.sql` — таблица notifications
- `002_conversations.sql` — таблицы conversations + messages

---

## Learning DB

### Table: `quizzes`

```sql
CREATE TABLE IF NOT EXISTS quizzes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id  UUID NOT NULL,
    teacher_id UUID NOT NULL,
    title      VARCHAR(500) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `questions`

```sql
CREATE TABLE IF NOT EXISTS questions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id        UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    text           TEXT NOT NULL,
    options        JSONB NOT NULL,
    correct_option INTEGER NOT NULL,
    "order"        INTEGER NOT NULL DEFAULT 0,
    concept_id     UUID
);
```

---

### Table: `quiz_attempts`

```sql
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id     UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    student_id  UUID NOT NULL,
    answers     JSONB NOT NULL,
    score       NUMERIC(5,2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `flashcards`

```sql
CREATE TABLE IF NOT EXISTS flashcards (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL,
    front         TEXT NOT NULL,
    back          TEXT NOT NULL,
    course_id     UUID,
    concept_id    UUID,
    difficulty    REAL NOT NULL DEFAULT 0.3,
    stability     REAL NOT NULL DEFAULT 1.0,
    due_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_review   TIMESTAMPTZ,
    review_count  INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

FSRS parameters: `difficulty` (0–1), `stability` (retention decay), `due_at` (next review date).

---

### Table: `review_logs`

```sql
CREATE TABLE IF NOT EXISTS review_logs (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flashcard_id UUID NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL,
    rating       SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 4),
    elapsed_days REAL NOT NULL DEFAULT 0,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Rating: 1=Again, 2=Hard, 3=Good, 4=Easy (FSRS scale).

---

### Table: `concepts`

```sql
CREATE TABLE IF NOT EXISTS concepts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL,
    name        VARCHAR(255) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    "order"     INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `concept_prerequisites`

```sql
CREATE TABLE IF NOT EXISTS concept_prerequisites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id      UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    prerequisite_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE(concept_id, prerequisite_id)
);
```

---

### Table: `concept_mastery`

```sql
CREATE TABLE IF NOT EXISTS concept_mastery (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    mastery    NUMERIC(5,4) NOT NULL DEFAULT 0.0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, concept_id)
);
```

Mastery: 0.0 to 1.0. Updated by quiz submission (score × 0.3) and mission completion.

---

### Table: `streaks`

```sql
CREATE TABLE IF NOT EXISTS streaks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL UNIQUE,
    current_streak  INTEGER NOT NULL DEFAULT 0,
    longest_streak  INTEGER NOT NULL DEFAULT 0,
    last_active_date DATE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `leaderboard_scores`

```sql
CREATE TABLE IF NOT EXISTS leaderboard_scores (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id   UUID NOT NULL,
    course_id UUID,
    score     INTEGER NOT NULL DEFAULT 0,
    period    VARCHAR(20) NOT NULL DEFAULT 'all_time',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, course_id, period)
);
```

---

### Table: `comments`

```sql
CREATE TABLE IF NOT EXISTS comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id       UUID NOT NULL,
    user_id         UUID NOT NULL,
    parent_id       UUID REFERENCES comments(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    is_pinned       BOOLEAN NOT NULL DEFAULT false,
    is_teacher_answer BOOLEAN NOT NULL DEFAULT false,
    upvote_count    INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Threaded replies: max 2 levels of nesting. Pinned and teacher_answer flags — teacher-only.

---

### Table: `comment_upvotes`

```sql
CREATE TABLE IF NOT EXISTS comment_upvotes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(comment_id, user_id)
);
```

---

### Table: `xp_ledger`

```sql
CREATE TABLE IF NOT EXISTS xp_ledger (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    amount     INTEGER NOT NULL,
    source     VARCHAR(50) NOT NULL,
    source_id  UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Source types: `lesson_complete` (10 XP), `quiz_submit` (20 XP), `flashcard_review` (5 XP), `mission_complete` (50 XP).

---

### Table: `badges`

```sql
CREATE TABLE IF NOT EXISTS badges (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    type       VARCHAR(50) NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}',
    earned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, type)
);
```

Badge types: `first_enrollment`, `streak_7`, `quiz_ace`, `mastery_100`, `first_mission`, `trust_level_up`.

---

### Table: `pretests`

```sql
CREATE TABLE IF NOT EXISTS pretests (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    course_id  UUID NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    result     JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, course_id)
);
```

---

### Table: `pretest_answers`

```sql
CREATE TABLE IF NOT EXISTS pretest_answers (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pretest_id UUID NOT NULL REFERENCES pretests(id) ON DELETE CASCADE,
    concept_id UUID NOT NULL,
    is_correct BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `activity_feed`

```sql
CREATE TABLE IF NOT EXISTS activity_feed (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    type       VARCHAR(50) NOT NULL,
    metadata   JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Activity types: `quiz_completed`, `flashcard_reviewed`, `badge_earned`, `streak_milestone`, `concept_mastered`, `mission_completed`.

---

### Table: `study_groups`

```sql
CREATE TABLE IF NOT EXISTS study_groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL,
    name        VARCHAR(200) NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_by  UUID NOT NULL,
    max_members INTEGER NOT NULL DEFAULT 10,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### Table: `study_group_members`

```sql
CREATE TABLE IF NOT EXISTS study_group_members (
    id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id  UUID NOT NULL REFERENCES study_groups(id) ON DELETE CASCADE,
    user_id   UUID NOT NULL,
    joined_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(group_id, user_id)
);
```

---

### Table: `certificates`

```sql
CREATE TABLE IF NOT EXISTS certificates (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    course_id   UUID NOT NULL,
    certificate_number VARCHAR(50) NOT NULL UNIQUE,
    issued_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, course_id)
);
```

---

### Table: `missions` (NEW)

```sql
CREATE TABLE IF NOT EXISTS missions (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL,
    organization_id   UUID NOT NULL,
    concept_id        UUID,
    title             VARCHAR(500) NOT NULL,
    description       TEXT NOT NULL DEFAULT '',
    mission_type      VARCHAR(50) NOT NULL DEFAULT 'general',
    difficulty        VARCHAR(20) NOT NULL DEFAULT 'intermediate',
    estimated_minutes INTEGER NOT NULL DEFAULT 15,
    status            VARCHAR(20) NOT NULL DEFAULT 'pending',
    score             INTEGER,
    xp_earned         INTEGER,
    time_spent_minutes INTEGER,
    started_at        TIMESTAMPTZ,
    completed_at      TIMESTAMPTZ,
    mission_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | Пользователь |
| `organization_id` | UUID | NOT NULL | Организация |
| `concept_id` | UUID | nullable | Привязанный концепт |
| `title` | VARCHAR(500) | NOT NULL | Название миссии |
| `description` | TEXT | NOT NULL, DEFAULT '' | Описание |
| `mission_type` | VARCHAR(50) | NOT NULL, DEFAULT 'general' | Тип: code_review, debugging, implementation, quiz, general |
| `difficulty` | VARCHAR(20) | NOT NULL, DEFAULT 'intermediate' | beginner, intermediate, advanced |
| `estimated_minutes` | INTEGER | NOT NULL, DEFAULT 15 | Оценочное время |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending, in_progress, completed, skipped |
| `score` | INTEGER | nullable | Оценка (0–100) |
| `xp_earned` | INTEGER | nullable | Заработанный XP |
| `time_spent_minutes` | INTEGER | nullable | Фактическое время |
| `started_at` | TIMESTAMPTZ | nullable | Время начала |
| `completed_at` | TIMESTAMPTZ | nullable | Время завершения |
| `mission_date` | DATE | NOT NULL, DEFAULT CURRENT_DATE | Дата миссии |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_missions_user_org (user_id, organization_id) + idx_missions_date (user_id, mission_date) + idx_missions_status.

---

### Table: `trust_levels` (NEW)

```sql
CREATE TABLE IF NOT EXISTS trust_levels (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL,
    organization_id     UUID NOT NULL,
    level               INTEGER NOT NULL DEFAULT 0 CHECK (level BETWEEN 0 AND 5),
    missions_completed  INTEGER NOT NULL DEFAULT 0,
    concepts_mastered   INTEGER NOT NULL DEFAULT 0,
    streak_days         INTEGER NOT NULL DEFAULT 0,
    discussions_count   INTEGER NOT NULL DEFAULT 0,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, organization_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | Пользователь |
| `organization_id` | UUID | NOT NULL | Организация |
| `level` | INTEGER | NOT NULL, DEFAULT 0, CHECK 0–5 | Trust level (0=Observer, 5=Expert) |
| `missions_completed` | INTEGER | NOT NULL, DEFAULT 0 | Количество выполненных миссий |
| `concepts_mastered` | INTEGER | NOT NULL, DEFAULT 0 | Количество освоенных концептов |
| `streak_days` | INTEGER | NOT NULL, DEFAULT 0 | Текущий streak |
| `discussions_count` | INTEGER | NOT NULL, DEFAULT 0 | Количество участий в дискуссиях |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата обновления |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE(user_id, organization_id) + idx_trust_org_id.

**Trust Level повышение:** автоматическое на основе missions_completed, concepts_mastered, streak_days, discussions_count.

**Миграции (Learning):**
- `001_quizzes.sql` — quizzes, questions, quiz_attempts
- `002_flashcards.sql` — flashcards, review_logs
- `003_concepts.sql` — concepts, concept_prerequisites, concept_mastery
- `004_streaks.sql` — streaks
- `005_leaderboard.sql` — leaderboard_scores
- `006_discussions.sql` — comments, comment_upvotes
- `007_xp_badges.sql` — xp_ledger, badges
- `008_pretests.sql` — pretests, pretest_answers
- `009_activity_feed.sql` — activity_feed
- `010_study_groups.sql` — study_groups, study_group_members
- `011_certificates.sql` — certificates
- `012_missions.sql` — таблица missions (NEW)
- `013_trust_levels.sql` — таблица trust_levels (NEW)

---

## RAG DB (NEW)

Новая база данных для RAG сервиса. Требует расширение `pgvector`.

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Table: `documents` (NEW)

```sql
CREATE TABLE IF NOT EXISTS documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    title           VARCHAR(500) NOT NULL,
    source_type     VARCHAR(50) NOT NULL DEFAULT 'manual',
    source_url      VARCHAR(2000),
    content_hash    VARCHAR(64),
    chunk_count     INTEGER NOT NULL DEFAULT 0,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `organization_id` | UUID | NOT NULL | Организация-владелец |
| `title` | VARCHAR(500) | NOT NULL | Название документа |
| `source_type` | VARCHAR(50) | NOT NULL, DEFAULT 'manual' | Тип: manual, github, upload |
| `source_url` | VARCHAR(2000) | nullable | URL источника (для GitHub) |
| `content_hash` | VARCHAR(64) | nullable | SHA-256 hash содержимого (для дедупликации) |
| `chunk_count` | INTEGER | NOT NULL, DEFAULT 0 | Количество chunks |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | pending, indexed, error |
| `metadata` | JSONB | NOT NULL, DEFAULT '{}' | Произвольные метаданные |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата обновления |

**Индексы:** PK (id) + idx_docs_org_id (organization_id) + idx_docs_source_type + idx_docs_content_hash.

---

### Table: `chunks` (NEW)

```sql
CREATE TABLE IF NOT EXISTS chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    embedding   vector(768),
    chunk_index INTEGER NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `document_id` | UUID | FK → documents(id) CASCADE, NOT NULL | Родительский документ |
| `content` | TEXT | NOT NULL | Текстовое содержимое chunk |
| `embedding` | vector(768) | nullable | Embedding вектор (Gemini Embedding) |
| `chunk_index` | INTEGER | NOT NULL | Порядковый номер chunk в документе |
| `metadata` | JSONB | NOT NULL, DEFAULT '{}' | Метаданные (file path, line numbers и т.д.) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_chunks_doc_id + ivfflat index на embedding для approximate nearest neighbor search.

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

### Table: `org_concepts` (NEW)

```sql
CREATE TABLE IF NOT EXISTS org_concepts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name            VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    importance      NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    document_ids    UUID[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(organization_id, name)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `organization_id` | UUID | NOT NULL | Организация |
| `name` | VARCHAR(255) | NOT NULL | Название концепта |
| `description` | TEXT | NOT NULL, DEFAULT '' | Описание |
| `importance` | NUMERIC(3,2) | NOT NULL, DEFAULT 0.5 | Важность (0.0–1.0) |
| `document_ids` | UUID[] | NOT NULL, DEFAULT '{}' | Связанные документы |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE(organization_id, name) + idx_org_concepts_org_id.

---

### Table: `concept_relationships` (NEW)

```sql
CREATE TABLE IF NOT EXISTS concept_relationships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_concept_id UUID NOT NULL REFERENCES org_concepts(id) ON DELETE CASCADE,
    to_concept_id   UUID NOT NULL REFERENCES org_concepts(id) ON DELETE CASCADE,
    relationship    VARCHAR(50) NOT NULL DEFAULT 'requires',
    strength        NUMERIC(3,2) NOT NULL DEFAULT 0.5,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(from_concept_id, to_concept_id, relationship)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `from_concept_id` | UUID | FK → org_concepts(id) CASCADE, NOT NULL | Исходный концепт |
| `to_concept_id` | UUID | FK → org_concepts(id) CASCADE, NOT NULL | Целевой концепт |
| `relationship` | VARCHAR(50) | NOT NULL, DEFAULT 'requires' | Тип: requires, extends, related_to |
| `strength` | NUMERIC(3,2) | NOT NULL, DEFAULT 0.5 | Сила связи (0.0–1.0) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE(from_concept_id, to_concept_id, relationship) + idx_cr_from + idx_cr_to.

---

### Table: `onboarding_templates` (NEW)

```sql
CREATE TABLE IF NOT EXISTS onboarding_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    name            VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    target_role     VARCHAR(100) NOT NULL,
    estimated_days  INTEGER NOT NULL DEFAULT 30,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `organization_id` | UUID | NOT NULL | Организация |
| `name` | VARCHAR(255) | NOT NULL | Название шаблона |
| `description` | TEXT | NOT NULL, DEFAULT '' | Описание |
| `target_role` | VARCHAR(100) | NOT NULL | Целевая роль: backend_engineer, frontend_engineer, devops и т.д. |
| `estimated_days` | INTEGER | NOT NULL, DEFAULT 30 | Оценочная продолжительность в днях |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Активен ли шаблон |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата обновления |

**Индексы:** PK (id) + idx_templates_org_id.

---

### Table: `template_stages` (NEW)

```sql
CREATE TABLE IF NOT EXISTS template_stages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id     UUID NOT NULL REFERENCES onboarding_templates(id) ON DELETE CASCADE,
    title           VARCHAR(255) NOT NULL,
    description     TEXT NOT NULL DEFAULT '',
    "order"         INTEGER NOT NULL DEFAULT 0,
    estimated_days  INTEGER NOT NULL DEFAULT 5,
    concept_ids     UUID[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `template_id` | UUID | FK → onboarding_templates(id) CASCADE, NOT NULL | Родительский шаблон |
| `title` | VARCHAR(255) | NOT NULL | Название этапа |
| `description` | TEXT | NOT NULL, DEFAULT '' | Описание |
| `order` | INTEGER | NOT NULL, DEFAULT 0 | Порядок |
| `estimated_days` | INTEGER | NOT NULL, DEFAULT 5 | Продолжительность |
| `concept_ids` | UUID[] | NOT NULL, DEFAULT '{}' | Привязанные концепты из org_concepts |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_stages_template_id.

**Миграции (RAG):**
- `001_documents.sql` — extension vector + таблица documents
- `002_chunks.sql` — таблица chunks + ivfflat index
- `003_org_concepts.sql` — org_concepts + concept_relationships
- `004_onboarding_templates.sql` — onboarding_templates + template_stages

---

## Dormant: Course DB

9 таблиц: `categories`, `courses`, `modules`, `lessons`, `reviews`, `course_bundles`, `bundle_courses`, `course_promotions`, `wishlist`. Код сохранён, не развивается. Детальные schemas доступны в git history.

## Dormant: Enrollment DB

2 таблицы: `enrollments`, `lesson_progress`. Код сохранён, не развивается.
