# Phase 3 — Growth (100K → 1M MAU)

> **Цель:** монетизация и масштабирование user base. Только после валидации
> Learning Intelligence (Phase 2). Реальные платежи, teacher tools, SEO, CI/CD.
>
> **Предусловие:** Phase 2 завершена — AI-фичи работают, completion > 40%.

---

## Бизнес-цели Phase 3

| Метрика | Целевое значение |
|---------|-----------------|
| MAU | 1 000 000 |
| Revenue / мес | $1.4M (10% paid × $14 ARPU) |
| Активные преподаватели | 10 000 |
| Курсов на платформе | 100 000 |
| Course completion rate | 50%+ |
| Paid conversion | 10% |

---

## Milestone 3.1 — Real Payments + Subscriptions

> Замена mock-оплаты на Stripe. Три тарифа. AI-кредиты привязаны к подписке.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| **Backend: Payment Service** | | | |
| 3.1.1 | Stripe SDK integration: create customer, payment intent, confirm | backend:payment | 🔴 |
| 3.1.2 | Subscription model: plans table (free/student/pro), user_subscriptions table + migration | backend:payment | ✅ |
| 3.1.3 | POST /subscriptions/create {plan_id, payment_method_id} → create Stripe subscription | backend:payment | 🔴 |
| 3.1.4 | GET /subscriptions/me → current plan, status, next billing date | backend:payment | 🔴 |
| 3.1.5 | POST /subscriptions/cancel → cancel at period end | backend:payment | 🔴 |
| 3.1.6 | POST /webhooks/stripe → handle invoice.paid, invoice.payment_failed, customer.subscription.deleted | backend:payment | 🔴 |
| 3.1.7 | Upgrade POST /payments to use Stripe payment intents (backward compatible with free courses) | backend:payment | 🔴 |
| **Backend: AI Service** | | | |
| 3.1.8 | AI credit system: credits per plan (free=10/day, student=100/day, pro=unlimited) | backend:ai | ✅ |
| 3.1.9 | GET /ai/credits/me → remaining credits, plan tier, reset time | backend:ai | ✅ |
| 3.1.10 | Enforce credit limits on /ai/quiz/generate, /ai/tutor/chat, /ai/summary/generate | backend:ai | ✅ |
| **Frontend** | | | |
| 3.1.11 | Pricing page: 3 tiers with feature comparison, annual/monthly toggle | frontend:buyer | 🔴 |
| 3.1.12 | Checkout flow: Stripe Elements (card input), plan selection, confirmation | frontend:buyer | 🔴 |
| 3.1.13 | Account settings: current plan, billing history, cancel/upgrade buttons | frontend:buyer | 🔴 |
| 3.1.14 | Credit usage indicator in header (remaining AI credits) | frontend:buyer | 🔴 |
| 3.1.15 | Paywall UI: "Upgrade to unlock" on premium features when free tier exhausted | frontend:buyer | 🔴 |
| **Tests** | | | |
| 3.1.16 | Payment tests: subscription CRUD, webhook handling, Stripe mock | backend:payment | 🔴 |
| 3.1.17 | AI credit tests: limit enforcement, plan-based limits, reset logic | backend:ai | 🔴 |

**DB Schema (payment-db — расширение):**
```sql
CREATE TABLE subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) NOT NULL UNIQUE,   -- free, student, pro
    stripe_price_id VARCHAR(255),        -- Stripe price ID
    price_monthly DECIMAL(10,2) NOT NULL,
    price_yearly DECIMAL(10,2),
    ai_credits_daily INT NOT NULL,       -- 10, 100, -1 (unlimited)
    features JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE user_subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id),
    stripe_subscription_id VARCHAR(255),
    stripe_customer_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active, canceled, past_due
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_user_subscriptions_user ON user_subscriptions(user_id);
CREATE INDEX idx_user_subscriptions_stripe ON user_subscriptions(stripe_subscription_id);
```

---

## Milestone 3.2 — Seller App + Teacher Analytics

> Отдельное Next.js приложение для преподавателей. Аналитика, заработок, управление контентом.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| **Backend: Course Service** | | | |
| 3.2.1 | GET /courses/{course_id}/analytics → students_count, completion_rate, avg_rating, revenue | backend:course | ✅ |
| 3.2.2 | GET /courses/my/stats → aggregate stats across all teacher courses | backend:course | 🔴 |
| **Backend: Payment Service** | | | |
| 3.2.3 | Teacher earnings model: earnings table, commission_rate (platform takes 30%) | backend:payment | ✅ |
| 3.2.4 | GET /earnings/me → total earned, pending payout, paid out | backend:payment | ✅ |
| 3.2.5 | POST /payouts/request → request payout (min $50, Stripe Connect) | backend:payment | ✅ |
| **Frontend: Seller App** | | | |
| 3.2.6 | Seller App scaffold: Next.js App Router, Tailwind, shared packages | frontend:seller | 🔴 |
| 3.2.7 | Dashboard page: total students, revenue, completion rate, charts (recharts) | frontend:seller | 🔴 |
| 3.2.8 | Course management: list my courses, create/edit, module/lesson editor | frontend:seller | 🔴 |
| 3.2.9 | Analytics page: per-course metrics, student funnel, rating distribution | frontend:seller | 🔴 |
| 3.2.10 | Earnings page: balance, payout history, request payout button | frontend:seller | 🔴 |
| 3.2.11 | Teacher onboarding wizard: profile, first course, publish checklist | frontend:seller | 🔴 |
| **Tests** | | | |
| 3.2.12 | Course analytics tests: stats aggregation, permission checks | backend:course | ✅ |
| 3.2.13 | Earnings tests: commission calculation, payout request, min threshold | backend:payment | ✅ |

**DB Schema (payment-db — расширение):**
```sql
CREATE TABLE teacher_earnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    course_id UUID NOT NULL,
    payment_id UUID NOT NULL,
    gross_amount DECIMAL(10,2) NOT NULL,
    commission_rate DECIMAL(5,4) NOT NULL DEFAULT 0.3000,  -- 30%
    net_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, paid_out
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE payouts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    teacher_id UUID NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    stripe_transfer_id VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    requested_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_teacher_earnings_teacher ON teacher_earnings(teacher_id);
CREATE INDEX idx_payouts_teacher ON payouts(teacher_id);
```

---

## Milestone 3.3 — SEO + Marketing

> Органический трафик. Structured data, Open Graph, sitemap, Core Web Vitals.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| **Frontend: Buyer App** | | | |
| 3.3.1 | Dynamic meta tags: title, description per page (course, category, lesson) | frontend:buyer | 🔴 |
| 3.3.2 | Structured data: JSON-LD Course schema on course pages (schema.org/Course) | frontend:buyer | 🔴 |
| 3.3.3 | Open Graph + Twitter Card meta tags for social sharing (course image, title, description) | frontend:buyer | 🔴 |
| 3.3.4 | Dynamic sitemap.xml generation: /sitemap.xml → all courses, categories, static pages | frontend:buyer | 🔴 |
| 3.3.5 | robots.txt: allow crawlers, reference sitemap | frontend:buyer | 🔴 |
| 3.3.6 | Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1 — audit + optimize | frontend:buyer | 🔴 |
| 3.3.7 | Image optimization: next/image for course thumbnails, lazy loading, WebP | frontend:buyer | 🔴 |
| 3.3.8 | Landing page: hero section, value props, social proof, CTA, responsive | frontend:buyer | 🔴 |

---

## Milestone 3.4 — DevOps + Reliability

> CI/CD pipeline, staging, backups, structured logging, real email delivery.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| **Infra: CI/CD** | | | |
| 3.4.1 | GitHub Actions: lint (ruff check) on pull request | infra | 🔴 |
| 3.4.2 | GitHub Actions: test all 7 Python services on pull request | infra | 🔴 |
| 3.4.3 | GitHub Actions: build buyer + seller frontends on pull request | infra | 🔴 |
| 3.4.4 | GitHub Actions: build Docker images on merge to main | infra | 🔴 |
| **Infra: Staging** | | | |
| 3.4.5 | docker-compose.staging.yml: separate from prod, own DB instances | infra | 🔴 |
| 3.4.6 | Environment-based config: .env.staging with staging URLs and secrets | infra | 🔴 |
| **Backend: Reliability** | | | |
| 3.4.7 | Structured JSON logging: replace print/basic logging with structlog across all 7 services | backend:identity | 🔴 |
| 3.4.8 | Database backup script: pg_dump per service DB, cron schedule, S3 upload | infra | 🔴 |
| 3.4.9 | Database restore script: pg_restore from S3, test recovery | infra | 🔴 |
| **Backend: Notification Service** | | | |
| 3.4.10 | Email delivery via Resend API: replace stdout stub with real SMTP/API | backend:notification | 🔴 |
| 3.4.11 | Email templates: welcome, email verification, password reset (HTML + plain text) | backend:notification | 🔴 |
| 3.4.12 | POST /notifications/email → send via Resend, log delivery status | backend:notification | 🔴 |
| **Tests** | | | |
| 3.4.13 | Notification email tests: delivery mock, template rendering, error handling | backend:notification | 🔴 |

---

## Milestone 3.5 — Engagement

> Увеличение retention: сертификаты, email-напоминания, wishlist, рекомендации.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| **Backend: Learning Engine** | | | |
| 3.5.1 | Certificate model: certificates table + migration (user_id, course_id, issued_at, pdf_url) | backend:learning | 🔴 |
| 3.5.2 | POST /certificates/generate {course_id} → generate PDF certificate (reportlab/weasyprint) | backend:learning | 🔴 |
| 3.5.3 | GET /certificates/me → list my certificates | backend:learning | 🔴 |
| 3.5.4 | GET /certificates/{id}/download → serve PDF | backend:learning | 🔴 |
| 3.5.5 | Auto-generate certificate on course completion (100% lessons + all quizzes passed) | backend:learning | 🔴 |
| **Backend: Notification Service** | | | |
| 3.5.6 | Email notifications: welcome (on register), course completion, streak reminder | backend:notification | 🔴 |
| 3.5.7 | Scheduled notifications: 7-day inactive reminder, flashcard due reminder (daily cron) | backend:notification | 🔴 |
| **Backend: Course Service** | | | |
| 3.5.8 | Wishlist model: wishlist table (user_id, course_id) + migration | backend:course | 🔴 |
| 3.5.9 | POST /wishlist {course_id} → add to wishlist | backend:course | 🔴 |
| 3.5.10 | DELETE /wishlist/{course_id} → remove from wishlist | backend:course | 🔴 |
| 3.5.11 | GET /wishlist/me → my wishlist | backend:course | 🔴 |
| **Backend: Enrollment Service** | | | |
| 3.5.12 | Course recommendations: collaborative filtering (users who enrolled in X also enrolled in Y) | backend:enrollment | 🔴 |
| 3.5.13 | GET /recommendations/me → top 10 recommended courses based on enrollment history | backend:enrollment | 🔴 |
| **Frontend** | | | |
| 3.5.14 | Certificate download page + share to LinkedIn button | frontend:buyer | 🔴 |
| 3.5.15 | Wishlist heart icon on course cards, wishlist page in profile | frontend:buyer | 🔴 |
| 3.5.16 | Recommendations section on homepage and course page ("Students also enrolled in...") | frontend:buyer | 🔴 |
| **Tests** | | | |
| 3.5.17 | Certificate tests: generation, auto-issue on completion, PDF download | backend:learning | 🔴 |
| 3.5.18 | Wishlist tests: add/remove/list, duplicate prevention | backend:course | 🔴 |
| 3.5.19 | Recommendation tests: collaborative filtering logic, empty history edge case | backend:enrollment | 🔴 |

**DB Schema (learning-db — расширение):**
```sql
CREATE TABLE certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    course_id UUID NOT NULL,
    pdf_url TEXT,
    issued_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, course_id)
);

CREATE INDEX idx_certificates_user ON certificates(user_id);
```

**DB Schema (course-db — расширение):**
```sql
CREATE TABLE wishlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    course_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, course_id)
);

CREATE INDEX idx_wishlist_user ON wishlist(user_id);
```

---

## Критерии завершения Phase 3

- [ ] Реальные платежи работают (Stripe)
- [ ] 3 subscription tiers + AI credit system
- [ ] Seller App с аналитикой и payouts
- [ ] CI/CD pipeline (GitHub Actions: lint → test → build)
- [ ] Real email delivery (Resend)
- [ ] SEO: structured data, sitemap, Open Graph
- [ ] Certificates + wishlist + recommendations
- [ ] Revenue > $100K/мес (target)
- [ ] 10K+ активных преподавателей (target)

---

## Точки соприкосновения с оркестратором

Оркестратор (`tools/orchestrator/`) парсит эту документацию для генерации задач:

1. **Таблицы задач** — строки `| номер | название | scope | статус |` → `Task` объекты
2. **Scope** → определяет test command (backend:payment → `pytest tests/ -v` в payment)
3. **Статус** → `🔴` = pending, `✅` = skip, `⏭️` = skip
4. **Зависимости** → frontend задачи автоматически зависят от backend задач в том же milestone
5. **DB Schema** → контекст для Claude Code промпта (передаётся вместе с задачей)

**После реализации каждой задачи оркестратор:**
- Меняет статус `🔴` → `✅` (в state.json, не в этом файле)
- Запускает тесты (`_infer_test_command`)
- Создаёт атомарный git commit

**Документы, которые нужно обновить после завершения milestone:**

| Milestone | Файлы для обновления |
|-----------|---------------------|
| 3.1 | `02-API-REFERENCE.md` (новые endpoints), `03-DATABASE-SCHEMAS.md` (plans, subscriptions), `05-INFRASTRUCTURE.md` (Stripe env vars) |
| 3.2 | `01-SYSTEM-OVERVIEW.md` (Seller App в диаграмме), `02-API-REFERENCE.md`, `03-DATABASE-SCHEMAS.md`, `STRUCTURE.md` (apps/seller/) |
| 3.3 | `01-SYSTEM-OVERVIEW.md` (SEO), `README.md` (landing page) |
| 3.4 | `05-INFRASTRUCTURE.md` (CI/CD, staging, backups), `TECHNICAL-OVERVIEW.md` (email delivery) |
| 3.5 | `02-API-REFERENCE.md`, `03-DATABASE-SCHEMAS.md` (certificates, wishlist) |
