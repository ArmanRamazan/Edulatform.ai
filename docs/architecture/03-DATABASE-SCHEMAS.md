# 03 — Database Schemas

> Последнее обновление: 2026-03-04
> Стадия: Phase 2.4 (Gamification — complete), Phase 2.5 (MVP Polish — in progress)

---

## Принцип: Database-per-Service

Каждый сервис владеет собственной PostgreSQL базой. Прямой доступ к БД другого сервиса запрещён.

```
identity-db (PostgreSQL 16 Alpine, :5433)
  └── database: identity
       ├── table: users
       ├── table: refresh_tokens
       ├── table: email_verification_tokens
       ├── table: password_reset_tokens
       ├── table: referrals
       └── table: follows

course-db (PostgreSQL 16 Alpine, :5434)
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

enrollment-db (PostgreSQL 16 Alpine, :5435)
  └── database: enrollment
       ├── table: enrollments
       └── table: lesson_progress

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
       └── table: gift_purchases

notification-db (PostgreSQL 16 Alpine, :5437)
  └── database: notification
       └── table: notifications

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
       └── table: certificates
```

**Итого: 38 таблиц в 6 базах данных.**

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
| `is_public` | BOOLEAN | NOT NULL, DEFAULT true | Видимость публичного профиля |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (email) + UNIQUE (referral_code).

**Миграции:**
- `001_users.sql` — создание таблицы users
- `002_add_role.sql` — добавление role ENUM и is_verified
- `003_add_admin_role.sql` — добавление значения `admin` в ENUM user_role
- `004_refresh_tokens.sql` — таблица refresh_tokens + индексы
- `005_email_verification.sql` — email_verified column + email_verification_tokens table
- `006_password_reset.sql` — password_reset_tokens table
- `007_referrals.sql` — referral_code column в users + таблица referrals
- `008_add_is_public.sql` — is_public column для управления видимостью профиля
- `009_follows.sql` — таблица follows для системы подписок

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

**Token rotation:** при каждом refresh все токены в family отзываются, создаётся новый с тем же family_id. При повторном использовании отозванного токена — вся family блокируется (reuse detection).

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

TTL: 24 часа. При регистрации создаётся токен; raw token логируется `[EMAIL_VERIFY]` (stub, без реальной отправки).

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

TTL: 1 час. Rate limit: 3 запроса в час на пользователя (silent ignore). После сброса пароля все refresh tokens отзываются.

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

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `referrer_id` | UUID | FK → users(id) CASCADE, NOT NULL | Пользователь, который пригласил |
| `referee_id` | UUID | FK → users(id) CASCADE, NOT NULL | Приглашённый пользователь |
| `referral_code` | VARCHAR(12) | NOT NULL | Реферальный код (REF-XXXXXXXX) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Статус: pending, completed |
| `reward_type` | VARCHAR(50) | — | Тип награды (если выдана) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `completed_at` | TIMESTAMPTZ | — | Дата завершения реферала |

**Индексы:** PK (id) + idx_referrals_referrer_id + idx_referrals_referee_id.

### Table: `follows`

```sql
CREATE TABLE IF NOT EXISTS follows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    follower_id UUID NOT NULL REFERENCES users(id),
    following_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(follower_id, following_id)
);
```

| Поле | Тип | Ограничения | Описание |
|------|-----|-------------|----------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() | Идентификатор записи |
| `follower_id` | UUID | NOT NULL, FK → users(id) | Кто подписался |
| `following_id` | UUID | NOT NULL, FK → users(id) | На кого подписался |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата подписки |

**Constraint:** UNIQUE(follower_id, following_id) — один пользователь не может подписаться дважды.

**Индексы:** PK (id) + idx_follows_follower + idx_follows_following.

---

## Course DB

### Table: `categories`

```sql
CREATE TABLE IF NOT EXISTS categories (
    id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE
);
```

Seed data: Programming, Design, Business, Marketing, Data Science, Languages, Music, Other.

### ENUM: `course_level`

```sql
CREATE TYPE course_level AS ENUM ('beginner', 'intermediate', 'advanced');
```

### Table: `courses`

```sql
CREATE TABLE IF NOT EXISTS courses (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id       UUID NOT NULL,
    title            VARCHAR(500) NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    is_free          BOOLEAN NOT NULL DEFAULT true,
    price            NUMERIC(12,2),
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    level            course_level NOT NULL DEFAULT 'beginner',
    avg_rating       NUMERIC(3,2),
    review_count     INTEGER NOT NULL DEFAULT 0,
    category_id      UUID REFERENCES categories(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `teacher_id` | UUID | NOT NULL | ID преподавателя (из Identity) |
| `title` | VARCHAR(500) | NOT NULL | Название курса |
| `description` | TEXT | NOT NULL, DEFAULT '' | Описание курса |
| `is_free` | BOOLEAN | NOT NULL, DEFAULT true | Бесплатный курс |
| `price` | NUMERIC(12,2) | nullable | Цена (если не бесплатный) |
| `duration_minutes` | INTEGER | NOT NULL, DEFAULT 0 | Длительность в минутах |
| `level` | course_level | NOT NULL, DEFAULT 'beginner' | Уровень сложности |
| `avg_rating` | NUMERIC(3,2) | nullable | Средний рейтинг (денормализация) |
| `review_count` | INTEGER | NOT NULL, DEFAULT 0 | Количество отзывов (денормализация) |
| `category_id` | UUID | nullable, FK → categories(id) | Категория курса |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_courses_teacher_id + idx_courses_category_id + GIN (title, description) через pg_trgm. `teacher_id` не имеет FK constraint — eventual consistency.

**Поиск:** `ILIKE '%query%'` по title и description. pg_trgm GIN index обеспечивает p99 < 50ms на 100K курсов.

**Миграции:**
- `001_courses.sql` — создание ENUM course_level и таблицы courses
- `002_modules_lessons.sql` — таблицы modules и lessons
- `003_reviews.sql` — таблица reviews + avg_rating/review_count в courses
- `004_indexes.sql` — FK indexes (teacher_id, course_id, module_id, student_id)
- `005_pg_trgm.sql` — pg_trgm extension + GIN index на courses (title, description)
- `006_categories.sql` — таблица categories + seed data + category_id FK на courses
- `008_bundles.sql` — таблицы course_bundles и bundle_courses
- `009_promotions.sql` — таблица course_promotions с индексами
- `010_wishlist.sql` — таблица wishlist (user_id + course_id UNIQUE)

### Table: `modules`

```sql
CREATE TABLE IF NOT EXISTS modules (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id  UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title      VARCHAR(500) NOT NULL,
    "order"    INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Table: `lessons`

```sql
CREATE TABLE IF NOT EXISTS lessons (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_id        UUID NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title            VARCHAR(500) NOT NULL,
    content          TEXT NOT NULL DEFAULT '',
    video_url        VARCHAR(2000),
    duration_minutes INTEGER NOT NULL DEFAULT 0,
    "order"          INTEGER NOT NULL DEFAULT 0,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Table: `reviews`

```sql
CREATE TABLE IF NOT EXISTS reviews (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id  UUID NOT NULL,
    rating     SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment    TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(student_id, course_id)
);
```

**Денормализация:** `courses.avg_rating` (NUMERIC(3,2)) и `courses.review_count` (INTEGER) обновляются при создании review.

### Table: `course_bundles`

```sql
CREATE TABLE IF NOT EXISTS course_bundles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id       UUID NOT NULL,
    title            VARCHAR(200) NOT NULL,
    description      TEXT NOT NULL DEFAULT '',
    price            NUMERIC(10,2) NOT NULL,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 99),
    is_active        BOOLEAN NOT NULL DEFAULT true,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**Индексы:** PK (id) + idx_bundles_teacher (teacher_id).

### Table: `bundle_courses`

```sql
CREATE TABLE IF NOT EXISTS bundle_courses (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bundle_id  UUID NOT NULL REFERENCES course_bundles(id) ON DELETE CASCADE,
    course_id  UUID NOT NULL,
    UNIQUE(bundle_id, course_id)
);
```

**Индексы:** PK (id) + idx_bc_bundle (bundle_id) + UNIQUE(bundle_id, course_id).

### Table: `course_promotions`

```sql
CREATE TABLE IF NOT EXISTS course_promotions (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id        UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    discount_percent INTEGER NOT NULL CHECK (discount_percent BETWEEN 1 AND 99),
    starts_at        TIMESTAMPTZ NOT NULL,
    ends_at          TIMESTAMPTZ NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_at > starts_at)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `course_id` | UUID | FK → courses(id) CASCADE, NOT NULL | Курс, к которому применяется акция |
| `discount_percent` | INTEGER | NOT NULL, CHECK 1–99 | Скидка в процентах |
| `starts_at` | TIMESTAMPTZ | NOT NULL | Начало действия акции |
| `ends_at` | TIMESTAMPTZ | NOT NULL | Конец действия акции |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_promotions_course_id (course_id) + idx_promotions_active (course_id, starts_at, ends_at) для быстрого поиска активных акций.

**Бизнес-логика:** Активная акция — запись где `starts_at <= now() <= ends_at`. `CourseResponse` включает `active_promotion` с полями `discount_percent`, `starts_at`, `ends_at` (null если нет активной акции). Просроченные акции деактивируются при запросе — `get_active` возвращает только текущие.

**Миграция:** `009_promotions.sql`.

### Table: `wishlist`

```sql
CREATE TABLE IF NOT EXISTS wishlist (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    course_id  UUID NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, course_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | Пользователь, добавивший курс |
| `course_id` | UUID | FK → courses(id) CASCADE, NOT NULL | Курс в вишлисте |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата добавления |

**Индексы:** PK (id) + UNIQUE(user_id, course_id) + idx_wishlist_user_id (user_id).

**Бизнес-логика:** Один пользователь может добавить один курс в вишлист один раз. При удалении курса запись автоматически удаляется (CASCADE).

**Миграция:** `010_wishlist.sql`.

---

## Enrollment DB

### ENUM: `enrollment_status`

```sql
CREATE TYPE enrollment_status AS ENUM ('enrolled', 'in_progress', 'completed');
```

### Table: `enrollments`

```sql
CREATE TABLE IF NOT EXISTS enrollments (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id    UUID NOT NULL,
    course_id     UUID NOT NULL,
    payment_id    UUID,
    status        enrollment_status NOT NULL DEFAULT 'enrolled',
    enrolled_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    total_lessons INTEGER NOT NULL DEFAULT 0,
    UNIQUE(student_id, course_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `student_id` | UUID | NOT NULL | ID студента (из Identity) |
| `course_id` | UUID | NOT NULL | ID курса (из Course) |
| `payment_id` | UUID | nullable | ID оплаты (из Payment, для платных курсов) |
| `status` | enrollment_status | NOT NULL, DEFAULT 'enrolled' | Статус записи |
| `enrolled_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата записи |
| `total_lessons` | INTEGER | NOT NULL, DEFAULT 0 | Общее число уроков (для auto-completion) |

**Индексы:** PK (id) + UNIQUE (student_id, course_id). Нет FK constraints — eventual consistency.

**Миграции:**
- `001_enrollments.sql` — создание ENUM enrollment_status и таблицы enrollments
- `002_lesson_progress.sql` — таблица lesson_progress
- `003_indexes.sql` — FK indexes (student_id, course_id)
- `004_total_lessons.sql` — total_lessons column для auto-completion

**Auto-completion:** При записи передаётся `total_lessons`. После завершения урока ProgressService проверяет: если все уроки пройдены → status = COMPLETED; если первый урок → status = IN_PROGRESS.

### Table: `lesson_progress`

```sql
CREATE TABLE IF NOT EXISTS lesson_progress (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id   UUID NOT NULL,
    lesson_id    UUID NOT NULL,
    course_id    UUID NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(student_id, lesson_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `student_id` | UUID | NOT NULL | ID студента |
| `lesson_id` | UUID | NOT NULL | ID урока (из Course Service) |
| `course_id` | UUID | NOT NULL | ID курса (для быстрого подсчёта прогресса) |
| `completed_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Когда урок завершён |

**Индексы:** PK (id) + UNIQUE (student_id, lesson_id).

---

## Payment DB

### ENUM: `payment_status`

```sql
CREATE TYPE payment_status AS ENUM ('pending', 'completed', 'failed', 'refunded');
```

### Table: `payments`

```sql
CREATE TABLE IF NOT EXISTS payments (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    course_id  UUID NOT NULL,
    amount     NUMERIC(12,2) NOT NULL,
    status     payment_status NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `student_id` | UUID | NOT NULL | ID студента |
| `course_id` | UUID | NOT NULL | ID курса |
| `amount` | NUMERIC(12,2) | NOT NULL | Сумма оплаты |
| `status` | payment_status | NOT NULL, DEFAULT 'completed' | Статус (MVP: всегда completed) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата оплаты |

**Миграции:**
- `001_payments.sql` — создание ENUM payment_status и таблицы payments
- `002_subscription_plans.sql` — таблицы subscription_plans и user_subscriptions
- `004_earnings_payouts.sql` — таблицы teacher_earnings и payouts
- `005_coupons.sql` — таблицы coupons и coupon_usages
- `006_refunds.sql` — таблица refunds
- `007_gifts.sql` — таблица gift_purchases

### Table: `subscription_plans`

```sql
CREATE TABLE IF NOT EXISTS subscription_plans (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(50) NOT NULL UNIQUE,
    stripe_price_id  VARCHAR(255),
    price_monthly    NUMERIC(10,2) NOT NULL DEFAULT 0,
    price_yearly     NUMERIC(10,2) NOT NULL DEFAULT 0,
    ai_credits_daily INTEGER NOT NULL DEFAULT 0,
    features         JSONB NOT NULL DEFAULT '[]',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `name` | VARCHAR(50) | UNIQUE, NOT NULL | Название плана: free, student, pro |
| `stripe_price_id` | VARCHAR(255) | nullable | ID цены в Stripe |
| `price_monthly` | NUMERIC(10,2) | NOT NULL, DEFAULT 0 | Цена в месяц |
| `price_yearly` | NUMERIC(10,2) | NOT NULL, DEFAULT 0 | Цена в год |
| `ai_credits_daily` | INTEGER | NOT NULL, DEFAULT 0 | Лимит AI-кредитов в день |
| `features` | JSONB | NOT NULL, DEFAULT '[]' | Список функций плана |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

### Table: `user_subscriptions`

```sql
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL UNIQUE,
    plan_id                 UUID NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id  VARCHAR(255),
    stripe_customer_id      VARCHAR(255),
    status                  VARCHAR(50) NOT NULL DEFAULT 'active',
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    cancel_at_period_end    BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | UNIQUE, NOT NULL | Одна подписка на пользователя |
| `plan_id` | UUID | FK → subscription_plans(id), NOT NULL | Текущий план |
| `stripe_subscription_id` | VARCHAR(255) | nullable | ID подписки в Stripe |
| `stripe_customer_id` | VARCHAR(255) | nullable | ID клиента в Stripe |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'active' | Статус: active, canceled, past_due |
| `current_period_start` | TIMESTAMPTZ | nullable | Начало текущего периода |
| `current_period_end` | TIMESTAMPTZ | nullable | Конец текущего периода |
| `cancel_at_period_end` | BOOLEAN | NOT NULL, DEFAULT false | Отмена в конце периода |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата последнего обновления |

**Индексы:** PK (id) + UNIQUE (user_id) + idx_user_subscriptions_plan_id.

### Table: `teacher_earnings`

```sql
CREATE TABLE IF NOT EXISTS teacher_earnings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id      UUID NOT NULL,
    course_id       UUID NOT NULL,
    payment_id      UUID NOT NULL UNIQUE,
    gross_amount    DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,4) NOT NULL DEFAULT 0.3000,
    net_amount      DECIMAL(10,2) NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `teacher_id` | UUID | NOT NULL | ID преподавателя (из Identity) |
| `course_id` | UUID | NOT NULL | ID курса (из Course) |
| `payment_id` | UUID | UNIQUE, NOT NULL | ID оплаты (из payments); один earning на оплату |
| `gross_amount` | DECIMAL(10,2) | NOT NULL | Полная сумма оплаты |
| `commission_rate` | DECIMAL(5,4) | NOT NULL, DEFAULT 0.3000 | Комиссия платформы (30%) |
| `net_amount` | DECIMAL(10,2) | NOT NULL | Сумма после вычета комиссии |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Статус: pending, paid |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (payment_id) + idx_teacher_earnings_teacher_id.

### Table: `payouts`

```sql
CREATE TABLE IF NOT EXISTS payouts (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id         UUID NOT NULL,
    amount             DECIMAL(10,2) NOT NULL,
    stripe_transfer_id VARCHAR(255),
    status             VARCHAR(20) NOT NULL DEFAULT 'pending',
    requested_at       TIMESTAMPTZ DEFAULT now(),
    completed_at       TIMESTAMPTZ
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `teacher_id` | UUID | NOT NULL | ID преподавателя (из Identity) |
| `amount` | DECIMAL(10,2) | NOT NULL | Сумма выплаты |
| `stripe_transfer_id` | VARCHAR(255) | nullable | ID трансфера в Stripe |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'pending' | Статус: pending, completed, failed |
| `requested_at` | TIMESTAMPTZ | DEFAULT now() | Дата запроса |
| `completed_at` | TIMESTAMPTZ | nullable | Дата завершения |

**Индексы:** PK (id) + idx_payouts_teacher_id.

### Table: `coupons`

```sql
CREATE TABLE IF NOT EXISTS coupons (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code           VARCHAR(50) NOT NULL UNIQUE,
    discount_type  VARCHAR(20) NOT NULL CHECK (discount_type IN ('percentage', 'fixed')),
    discount_value DECIMAL(10,2) NOT NULL CHECK (discount_value > 0),
    max_uses       INT,
    current_uses   INT NOT NULL DEFAULT 0,
    valid_from     TIMESTAMPTZ NOT NULL,
    valid_until    TIMESTAMPTZ NOT NULL,
    course_id      UUID,
    created_by     UUID NOT NULL,
    is_active      BOOLEAN NOT NULL DEFAULT true,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (valid_until > valid_from)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `code` | VARCHAR(50) | UNIQUE, NOT NULL | Промокод (uppercase alphanumeric + hyphens) |
| `discount_type` | VARCHAR(20) | NOT NULL, CHECK | Тип скидки: percentage или fixed |
| `discount_value` | DECIMAL(10,2) | NOT NULL, > 0 | Значение скидки (% или фикс. сумма) |
| `max_uses` | INT | nullable | Лимит использований (null = безлимит) |
| `current_uses` | INT | NOT NULL, DEFAULT 0 | Текущее кол-во использований |
| `valid_from` | TIMESTAMPTZ | NOT NULL | Начало действия |
| `valid_until` | TIMESTAMPTZ | NOT NULL | Окончание действия |
| `course_id` | UUID | nullable | Привязка к курсу (null = все курсы) |
| `created_by` | UUID | NOT NULL | ID администратора-создателя |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Активен ли купон |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (code).

### Table: `coupon_usages`

```sql
CREATE TABLE IF NOT EXISTS coupon_usages (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id  UUID NOT NULL REFERENCES coupons(id),
    user_id    UUID NOT NULL,
    payment_id UUID,
    used_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(coupon_id, user_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `coupon_id` | UUID | FK → coupons(id), NOT NULL | ID купона |
| `user_id` | UUID | NOT NULL | ID пользователя |
| `payment_id` | UUID | nullable | ID оплаты |
| `used_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата использования |

**Индексы:** PK (id) + UNIQUE (coupon_id, user_id).

### Table: `refunds`

```sql
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id UUID NOT NULL UNIQUE REFERENCES payments(id),
    user_id UUID NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'requested'
        CHECK (status IN ('requested', 'approved', 'rejected', 'processed')),
    amount DECIMAL(10,2) NOT NULL,
    admin_note TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `payment_id` | UUID | FK → payments(id), NOT NULL, UNIQUE | ID оплаты (одна заявка на оплату) |
| `user_id` | UUID | NOT NULL | ID пользователя-заявителя |
| `reason` | TEXT | NOT NULL | Причина возврата |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'requested' | Статус: requested, approved, rejected, processed |
| `amount` | DECIMAL(10,2) | NOT NULL | Сумма возврата |
| `admin_note` | TEXT | nullable | Комментарий администратора |
| `requested_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата подачи заявки |
| `processed_at` | TIMESTAMPTZ | nullable | Дата обработки заявки |

**Индексы:** PK (id) + UNIQUE (payment_id) + idx_refunds_user (user_id) + idx_refunds_status (status).

**Бизнес-правила:**
- Одна заявка на возврат на одну оплату (UNIQUE payment_id)
- Только владелец оплаты может подать заявку
- Возврат доступен в течение 14 дней после оплаты
- Только admin может одобрить/отклонить заявку
- При одобрении статус оплаты меняется на 'refunded'

---

### Table: `gift_purchases`

```sql
CREATE TABLE IF NOT EXISTS gift_purchases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id UUID NOT NULL,
    recipient_email VARCHAR(255) NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID REFERENCES payments(id),
    gift_code VARCHAR(50) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'purchased'
        CHECK (status IN ('purchased', 'redeemed', 'expired')),
    message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    redeemed_at TIMESTAMPTZ,
    redeemed_by UUID,
    expires_at TIMESTAMPTZ NOT NULL
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `buyer_id` | UUID | NOT NULL | ID покупателя-дарителя |
| `recipient_email` | VARCHAR(255) | NOT NULL | Email получателя подарка |
| `course_id` | UUID | NOT NULL | ID подаренного курса |
| `payment_id` | UUID | FK → payments(id), nullable | ID связанной оплаты |
| `gift_code` | VARCHAR(50) | NOT NULL, UNIQUE | Уникальный код активации |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'purchased' | Статус: purchased, redeemed, expired |
| `message` | TEXT | nullable | Персональное сообщение от дарителя |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания подарка |
| `redeemed_at` | TIMESTAMPTZ | nullable | Дата активации подарка |
| `redeemed_by` | UUID | nullable | ID пользователя, активировавшего подарок |
| `expires_at` | TIMESTAMPTZ | NOT NULL | Дата истечения срока действия кода |

**Индексы:** PK (id) + UNIQUE (gift_code) + idx_gift_purchases_buyer (buyer_id) + idx_gift_purchases_recipient (recipient_email).

**Бизнес-правила:**
- Каждый подарок имеет уникальный код формата `GIFT-XXXX-XXXX-XXXX`
- Код может быть активирован только один раз (status: purchased → redeemed)
- Срок действия кода — 30 дней с момента покупки
- Активировать подарок может любой аутентифицированный пользователь
- Истёкшие коды имеют status 'expired' и не могут быть активированы

**Миграция:** `007_gifts.sql`

---

## Notification DB

### ENUM: `notification_type`

```sql
CREATE TYPE notification_type AS ENUM ('registration', 'enrollment', 'payment', 'streak_reminder', 'flashcard_reminder', 'welcome', 'course_completed', 'review_received', 'streak_at_risk');
```

### Table: `notifications`

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    type       notification_type NOT NULL,
    title      VARCHAR(500) NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    is_read    BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    email_sent BOOLEAN DEFAULT false
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | ID пользователя |
| `type` | notification_type | NOT NULL | Тип уведомления |
| `title` | VARCHAR(500) | NOT NULL | Заголовок |
| `body` | TEXT | NOT NULL, DEFAULT '' | Тело уведомления |
| `is_read` | BOOLEAN | NOT NULL, DEFAULT false | Прочитано |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `email_sent` | BOOLEAN | DEFAULT false | Email-уведомление отправлено |

**Email:** Для lifecycle-типов (welcome, course_completed, review_received, streak_at_risk) при наличии email отправляется уведомление через EmailAdapter (логирование в stdout). Результат сохраняется в `email_sent`.

### Table: `conversations`

```sql
CREATE TABLE IF NOT EXISTS conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    participant_1   UUID NOT NULL,
    participant_2   UUID NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_message_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(participant_1, participant_2)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `participant_1` | UUID | NOT NULL | ID первого участника (меньший UUID) |
| `participant_2` | UUID | NOT NULL | ID второго участника (больший UUID) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `last_message_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время последнего сообщения |

### Table: `messages`

```sql
CREATE TABLE IF NOT EXISTS messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    sender_id       UUID NOT NULL,
    content         TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `conversation_id` | UUID | NOT NULL, FK → conversations | ID диалога |
| `sender_id` | UUID | NOT NULL | ID отправителя |
| `content` | TEXT | NOT NULL | Текст сообщения (1-2000 символов) |
| `is_read` | BOOLEAN | NOT NULL, DEFAULT false | Прочитано получателем |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Миграции:**
- `001_notifications.sql` — создание ENUM notification_type и таблицы notifications
- `003_streak_reminder_type.sql` — добавление `streak_reminder` в ENUM notification_type
- `004_flashcard_reminder_type.sql` — добавление `flashcard_reminder` в ENUM notification_type
- `005_conversations.sql` — создание таблицы conversations с индексами по participant_1, participant_2
- `006_messages.sql` — создание таблицы messages с индексом по conversation_id
- `007_email_sent.sql` — добавление колонки `email_sent` и новых типов `welcome`, `course_completed`, `review_received`, `streak_at_risk` в ENUM

---

## Learning DB

### Table: `quizzes`

```sql
CREATE TABLE IF NOT EXISTS quizzes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id  UUID NOT NULL UNIQUE,
    course_id  UUID NOT NULL,
    teacher_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `lesson_id` | UUID | UNIQUE, NOT NULL | ID урока (из Course Service); один квиз на урок |
| `course_id` | UUID | NOT NULL | ID курса (из Course Service) |
| `teacher_id` | UUID | NOT NULL | ID преподавателя-создателя (из Identity) |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (lesson_id). Нет FK constraints — eventual consistency.

### Table: `questions`

```sql
CREATE TABLE IF NOT EXISTS questions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id       UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
    text          TEXT NOT NULL,
    options       JSONB NOT NULL,
    correct_index INT NOT NULL,
    explanation   TEXT,
    "order"       INT NOT NULL DEFAULT 0
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `quiz_id` | UUID | FK → quizzes(id) CASCADE, NOT NULL | Квиз, которому принадлежит вопрос |
| `text` | TEXT | NOT NULL | Текст вопроса |
| `options` | JSONB | NOT NULL | Массив вариантов ответа (строки) |
| `correct_index` | INT | NOT NULL | Индекс правильного варианта в `options` |
| `explanation` | TEXT | nullable | Объяснение правильного ответа |
| `"order"` | INT | NOT NULL, DEFAULT 0 | Порядок вопроса в квизе |

**Индексы:** PK (id) + idx_questions_quiz_id.

### Table: `quiz_attempts`

```sql
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id      UUID NOT NULL REFERENCES quizzes(id),
    student_id   UUID NOT NULL,
    answers      JSONB NOT NULL,
    score        FLOAT NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `quiz_id` | UUID | FK → quizzes(id), NOT NULL | Квиз, по которому сделана попытка |
| `student_id` | UUID | NOT NULL | ID студента (из Identity) |
| `answers` | JSONB | NOT NULL | Массив выбранных индексов ответов (`int[]`) |
| `score` | FLOAT | NOT NULL | Доля правильных ответов (0.0–1.0) |
| `completed_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время завершения попытки |

**Индексы:** PK (id) + idx_quiz_attempts_quiz_student (quiz_id, student_id). Нет ограничения на количество попыток — студент может проходить квиз многократно.

### Table: `flashcards`

```sql
CREATE TABLE IF NOT EXISTS flashcards (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id  UUID NOT NULL,
    course_id   UUID NOT NULL,
    concept     TEXT NOT NULL,
    answer      TEXT NOT NULL,
    source_type VARCHAR(20),
    source_id   UUID,
    stability   FLOAT DEFAULT 0,
    difficulty  FLOAT DEFAULT 0,
    due         TIMESTAMPTZ DEFAULT now(),
    last_review TIMESTAMPTZ,
    reps        INT DEFAULT 0,
    lapses      INT DEFAULT 0,
    state       INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `student_id` | UUID | NOT NULL | ID студента (из Identity) |
| `course_id` | UUID | NOT NULL | ID курса (из Course) |
| `concept` | TEXT | NOT NULL | Вопрос (лицевая сторона карточки) |
| `answer` | TEXT | NOT NULL | Ответ (обратная сторона карточки) |
| `source_type` | VARCHAR(20) | nullable | Источник: manual, quiz_mistake, key_concept |
| `source_id` | UUID | nullable | ID источника (quiz question, etc.) |
| `stability` | FLOAT | DEFAULT 0 | FSRS stability parameter |
| `difficulty` | FLOAT | DEFAULT 0 | FSRS difficulty parameter |
| `due` | TIMESTAMPTZ | DEFAULT now() | Когда карточка должна быть повторена |
| `last_review` | TIMESTAMPTZ | nullable | Время последнего повторения |
| `reps` | INT | DEFAULT 0 | Количество повторений (FSRS step) |
| `lapses` | INT | DEFAULT 0 | Количество "забываний" (переходов в Relearning) |
| `state` | INT | DEFAULT 0 | FSRS состояние: 0=New, 1=Learning, 2=Review, 3=Relearning |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | Дата создания |

**Индексы:** PK (id) + idx_flashcards_student_due (student_id, due) + idx_flashcards_student_course (student_id, course_id).

### Table: `review_logs`

```sql
CREATE TABLE IF NOT EXISTS review_logs (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id            UUID REFERENCES flashcards(id) ON DELETE CASCADE,
    rating             INT NOT NULL,
    review_duration_ms INT,
    reviewed_at        TIMESTAMPTZ DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `card_id` | UUID | FK → flashcards(id) CASCADE | Карточка |
| `rating` | INT | NOT NULL | Оценка: 1=Again, 2=Hard, 3=Good, 4=Easy |
| `review_duration_ms` | INT | nullable | Время ответа в миллисекундах |
| `reviewed_at` | TIMESTAMPTZ | DEFAULT now() | Время повторения |

**Индексы:** PK (id) + idx_review_logs_card (card_id).

### Table: `concepts`

```sql
CREATE TABLE IF NOT EXISTS concepts (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL,
    lesson_id   UUID,
    name        VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    parent_id   UUID REFERENCES concepts(id) ON DELETE SET NULL,
    "order"     INT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE(course_id, name)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `course_id` | UUID | NOT NULL | ID курса (из Course Service) |
| `lesson_id` | UUID | nullable | ID урока, к которому привязан concept |
| `name` | VARCHAR(200) | NOT NULL | Название concept (уникально в рамках курса) |
| `description` | TEXT | DEFAULT '' | Описание concept |
| `parent_id` | UUID | nullable, FK → concepts(id) SET NULL | Родительский concept (иерархия) |
| `"order"` | INT | DEFAULT 0 | Порядок отображения |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | Дата создания |

**Индексы:** PK (id) + UNIQUE (course_id, name).

### Table: `concept_prerequisites`

```sql
CREATE TABLE IF NOT EXISTS concept_prerequisites (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    concept_id      UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    prerequisite_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    UNIQUE(concept_id, prerequisite_id),
    CHECK(concept_id != prerequisite_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `concept_id` | UUID | FK → concepts(id) CASCADE, NOT NULL | Concept, который требует prerequisite |
| `prerequisite_id` | UUID | FK → concepts(id) CASCADE, NOT NULL | Prerequisite concept |

**Индексы:** PK (id) + UNIQUE (concept_id, prerequisite_id). CHECK constraint запрещает self-reference.

### Table: `concept_mastery`

```sql
CREATE TABLE IF NOT EXISTS concept_mastery (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL,
    concept_id UUID NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
    mastery    FLOAT DEFAULT 0.0,
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(student_id, concept_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `student_id` | UUID | NOT NULL | ID студента (из Identity) |
| `concept_id` | UUID | FK → concepts(id) CASCADE, NOT NULL | Concept |
| `mastery` | FLOAT | DEFAULT 0.0 | Уровень владения (0.0–1.0) |
| `updated_at` | TIMESTAMPTZ | DEFAULT now() | Последнее обновление |

**Индексы:** PK (id) + UNIQUE (student_id, concept_id).

**Mastery algorithm:** при сдаче квиза (QuizService.submit_quiz) mastery обновляется автоматически: `mastery += score × 0.3`, capped at 1.0. Обновляются все concepts, привязанные к lesson_id квиза.

### Table: `streaks`

```sql
CREATE TABLE IF NOT EXISTS streaks (
    user_id            UUID PRIMARY KEY,
    current_streak     INT NOT NULL DEFAULT 1,
    longest_streak     INT NOT NULL DEFAULT 1,
    last_activity_date DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `user_id` | UUID | PK | ID пользователя (из Identity) |
| `current_streak` | INT | NOT NULL, DEFAULT 1 | Текущая серия дней подряд |
| `longest_streak` | INT | NOT NULL, DEFAULT 1 | Максимальная серия за всё время |
| `last_activity_date` | DATE | NOT NULL, DEFAULT CURRENT_DATE | Дата последней активности |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Последнее обновление |

**Индексы:** PK (user_id). Одна запись на пользователя.

**Бизнес-логика:** Первая активность — создаёт запись (current=1). Повторный вызов в тот же день — no-op. Consecutive day — инкремент current_streak. Gap >1 дня — сброс current_streak до 1. longest_streak обновляется при каждом инкременте. GET /streaks/me возвращает current_streak=0, если last_activity_date раньше вчерашнего дня.

### Table: `leaderboard_scores`

Opt-in leaderboard: рейтинг студентов внутри курса.

```sql
CREATE TABLE IF NOT EXISTS leaderboard_scores (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL,
    student_id  UUID NOT NULL,
    total_score INT NOT NULL DEFAULT 0,
    opt_in      BOOLEAN NOT NULL DEFAULT true,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(student_id, course_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `course_id` | UUID | NOT NULL | ID курса |
| `student_id` | UUID | NOT NULL | ID студента (из Identity) |
| `total_score` | INT | NOT NULL, DEFAULT 0 | Накопленные баллы |
| `opt_in` | BOOLEAN | NOT NULL, DEFAULT true | Участвует ли в рейтинге |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Последнее обновление |

**Индексы:** UNIQUE (student_id, course_id) + partial index на (course_id, total_score DESC) WHERE opt_in = TRUE — для быстрого получения топ-N.

**Бизнес-логика:** opt-in создаёт запись (total_score=0). Opt-out ставит opt_in=FALSE, total_score сохраняется. Leaderboard показывает только opt_in=TRUE записи, ранжированные по total_score DESC.

### Table: `comments`

```sql
CREATE TABLE IF NOT EXISTS comments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_id         UUID NOT NULL,
    course_id         UUID NOT NULL,
    user_id           UUID NOT NULL,
    content           TEXT NOT NULL,
    parent_id         UUID REFERENCES comments(id) ON DELETE CASCADE,
    upvote_count      INT NOT NULL DEFAULT 0,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_pinned         BOOLEAN NOT NULL DEFAULT false,
    is_teacher_answer BOOLEAN NOT NULL DEFAULT false
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `lesson_id` | UUID | NOT NULL | Урок, к которому относится комментарий |
| `course_id` | UUID | NOT NULL | Курс |
| `user_id` | UUID | NOT NULL | Автор комментария |
| `content` | TEXT | NOT NULL | Текст комментария (1–5000 символов) |
| `parent_id` | UUID | nullable, FK → comments(id) CASCADE | Ответ на комментарий (макс. 2 уровня) |
| `upvote_count` | INT | NOT NULL, DEFAULT 0 | Кэшированный счётчик upvotes |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата создания |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата последнего изменения |
| `is_pinned` | BOOLEAN | NOT NULL, DEFAULT false | Закреплённый комментарий (только teacher) |
| `is_teacher_answer` | BOOLEAN | NOT NULL, DEFAULT false | Ответ учителя (только teacher) |

**Индексы:** `idx_comments_lesson` (lesson_id, created_at DESC), `idx_comments_parent` (parent_id WHERE parent_id IS NOT NULL).

### Table: `comment_upvotes`

```sql
CREATE TABLE IF NOT EXISTS comment_upvotes (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comment_id UUID NOT NULL REFERENCES comments(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL,
    UNIQUE(comment_id, user_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `comment_id` | UUID | FK → comments(id) CASCADE, NOT NULL | Комментарий |
| `user_id` | UUID | NOT NULL | Кто поставил upvote |

**Индексы:** UNIQUE (comment_id, user_id) — один upvote от пользователя на комментарий.

**Бизнес-логика:** Upvote — toggle: повторный вызов снимает голос. upvote_count в comments обновляется при add/remove vote. Создание комментария любым авторизованным пользователем. Ответы через parent_id (макс. 2 уровня — ответ на ответ запрещён). Pin и mark-answer — только teacher. Threaded listing: pinned first, then teacher answers, then by date. Удаление каскадное (удаляет ответы и голоса).

### Table: `xp_ledger`

```sql
CREATE TABLE IF NOT EXISTS xp_ledger (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID NOT NULL,
    reason     VARCHAR(50) NOT NULL,
    amount     INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | Студент |
| `reason` | VARCHAR(50) | NOT NULL | Причина начисления: `lesson_complete`, `quiz_submit`, `flashcard_review` |
| `amount` | INT | NOT NULL | Количество XP: lesson_complete=10, quiz_submit=20, flashcard_review=5 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время начисления |

**Индексы:** `idx_xp_ledger_user_id` (user_id), `idx_xp_ledger_user_created` (user_id, created_at DESC).

**Бизнес-логика:** Append-only лог начислений XP. Суммарный XP вычисляется как SUM(amount) GROUP BY user_id. GET /xp/me возвращает total_xp, level (total_xp // 100 + 1) и xp_to_next_level.

### Table: `badges`

```sql
CREATE TABLE IF NOT EXISTS badges (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL,
    badge_type  VARCHAR(50) NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(user_id, badge_type)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | Студент |
| `badge_type` | VARCHAR(50) | NOT NULL, UNIQUE(user_id, badge_type) | Тип: `first_enrollment`, `streak_7`, `quiz_ace`, `mastery_100` |
| `unlocked_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время разблокировки |

**Индексы:** `idx_badges_user_id` (user_id), UNIQUE (user_id, badge_type).

**Badge types:**
- `first_enrollment` — первая запись на курс
- `streak_7` — 7 дней подряд активности
- `quiz_ace` — сдача квиза на 100%
- `mastery_100` — достижение 100% mastery по любому concept

### Table: `pretests`

```sql
CREATE TABLE IF NOT EXISTS pretests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL,
    course_id    UUID NOT NULL,
    status       VARCHAR(20) NOT NULL DEFAULT 'in_progress',
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | ID студента (из Identity) |
| `course_id` | UUID | NOT NULL | ID курса (из Course Service) |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'in_progress' | Статус: `in_progress`, `completed` |
| `started_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время начала |
| `completed_at` | TIMESTAMPTZ | nullable | Время завершения |

**Индексы:** PK (id) + idx_pretests_user_course (user_id, course_id).

### Table: `pretest_answers`

```sql
CREATE TABLE IF NOT EXISTS pretest_answers (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pretest_id     UUID NOT NULL REFERENCES pretests(id) ON DELETE CASCADE,
    concept_id     UUID NOT NULL,
    question       TEXT NOT NULL,
    user_answer    TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    is_correct     BOOLEAN NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `pretest_id` | UUID | FK → pretests(id) CASCADE, NOT NULL | Пре-тест, к которому относится ответ |
| `concept_id` | UUID | NOT NULL | Концепт, по которому задан вопрос (из concepts) |
| `question` | TEXT | NOT NULL | Текст вопроса |
| `user_answer` | TEXT | NOT NULL | Ответ студента |
| `correct_answer` | TEXT | NOT NULL | Правильный ответ |
| `is_correct` | BOOLEAN | NOT NULL | Верен ли ответ |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время ответа |

**Индексы:** PK (id) + idx_pretest_answers_pretest_id (pretest_id).

**Бизнес-логика:** Адаптивный алгоритм выбирает следующий концепт на основе истории ответов текущего пре-теста. При завершении всех концептов (или достижении лимита вопросов) pretest.status переводится в `completed` и вычисляется итоговый score = correct / total.

**Миграции:**
- `001_quizzes.sql` — создание таблиц quizzes, questions, quiz_attempts и индексов
- `002_flashcards.sql` — создание таблиц flashcards, review_logs и индексов
- `003_concepts.sql` — создание таблиц concepts, concept_prerequisites, concept_mastery и индексов
- `004_streaks.sql` — создание таблицы streaks
- `006_leaderboard.sql` — создание таблицы leaderboard_scores с partial index
- `007_discussions.sql` — создание таблиц comments, comment_upvotes с индексами
- `012_discussion_enhancements.sql` — добавление is_pinned, is_teacher_answer в comments
- `008_xp_badges.sql` — создание таблиц xp_ledger, badges с индексами
- `009_pretests.sql` — создание таблиц pretests, pretest_answers с индексами
- `010_activity_feed.sql` — создание таблицы activity_feed с индексами
- `011_study_groups.sql` — создание таблиц study_groups, study_group_members с индексами
- `013_certificates.sql` — создание таблицы certificates с индексами

### Table: `activity_feed`

```sql
CREATE TABLE IF NOT EXISTS activity_feed (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор |
| `user_id` | UUID | NOT NULL | Пользователь, совершивший действие |
| `activity_type` | VARCHAR(50) | NOT NULL | Тип: quiz_completed, flashcard_reviewed, badge_earned, streak_milestone, concept_mastered |
| `payload` | JSONB | NOT NULL, DEFAULT '{}' | Расширяемые данные по типу активности |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время события |

**Индексы:** PK (id) + idx_activity_feed_user (user_id, created_at DESC) + idx_activity_feed_created (created_at DESC).

**Бизнес-логика:** Записи создаются автоматически при завершении квизов, review флешкарт, получении бейджей, streak milestones и mastery концептов. Используется для ленты активности пользователя и социального фида.

### Table: `study_groups`

```sql
CREATE TABLE IF NOT EXISTS study_groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id   UUID NOT NULL,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    creator_id  UUID NOT NULL,
    max_members INT NOT NULL DEFAULT 10,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор группы |
| `course_id` | UUID | NOT NULL | Курс, к которому привязана группа |
| `name` | VARCHAR(100) | NOT NULL | Название группы (1–100 символов) |
| `description` | TEXT | nullable | Описание группы |
| `creator_id` | UUID | NOT NULL | Создатель группы |
| `max_members` | INT | NOT NULL, DEFAULT 10 | Максимум участников |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время создания |

**Индексы:** PK (id) + idx_study_groups_course (course_id).

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

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор записи |
| `group_id` | UUID | NOT NULL, FK → study_groups(id) CASCADE | Ссылка на группу |
| `user_id` | UUID | NOT NULL | Пользователь-участник |
| `joined_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Время вступления |

**Индексы:** PK (id) + UNIQUE(group_id, user_id) + idx_sgm_group (group_id) + idx_sgm_user (user_id).

**Бизнес-логика:** Создатель автоматически добавляется как первый участник. Создатель не может покинуть группу (предотвращение осиротевших групп). Новый участник не может вступить, если count >= max_members.

### Table: `certificates`

```sql
CREATE TABLE IF NOT EXISTS certificates (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL,
    course_id          UUID NOT NULL,
    issued_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    certificate_number VARCHAR(20) NOT NULL UNIQUE,
    template_data      JSONB DEFAULT '{}',
    UNIQUE(user_id, course_id)
);
```

| Column | Type | Constraints | Описание |
|--------|------|-------------|----------|
| `id` | UUID | PK, auto | Уникальный идентификатор сертификата |
| `user_id` | UUID | NOT NULL | Пользователь, получивший сертификат |
| `course_id` | UUID | NOT NULL | Курс, за который выдан сертификат |
| `issued_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now() | Дата выдачи |
| `certificate_number` | VARCHAR(20) | NOT NULL, UNIQUE | Уникальный номер формата CERT-YYYY-XXXXXX |
| `template_data` | JSONB | DEFAULT '{}' | Расширяемые данные шаблона |

**Индексы:** PK (id) + UNIQUE(certificate_number) + UNIQUE(user_id, course_id) + idx_certificates_user_id (user_id) + idx_certificates_course_id (course_id).

**Бизнес-логика:** Один сертификат на пару (user, course). Номер генерируется автоматически в формате CERT-{YYYY}-{6 случайных символов}. Дубликаты предотвращаются UNIQUE constraint.

---

## Connection Pool

Все сервисы используют `asyncpg.Pool`:
- `min_size = 5` (настраивается через `DB_POOL_MIN_SIZE`)
- `max_size = 20` (настраивается через `DB_POOL_MAX_SIZE`)

Pool увеличен с 5/5 до 5/20 в Phase 1.0 — saturation снизилась с 100% до 10%.

---

## Миграции

Forward-only SQL файлы. Запускаются автоматически при старте сервиса в `app/main.py` через `lifespan`:

```python
async with create_pool(settings.database_url) as pool:
    for sql_file in sorted(Path("migrations").glob("*.sql")):
        await pool.execute(sql_file.read_text())
```

Каждая миграция идемпотентна (`CREATE TABLE IF NOT EXISTS`, `CREATE TYPE IF NOT EXISTS`).
