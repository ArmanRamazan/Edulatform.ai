# 04 — Домены и Bounded Contexts

> Владелец: Architect / Principal Developer
> Последнее обновление: 2026-03-03

---

## Domain Map

```
┌─────────────────────────────────────────────────────────────────┐
│                       EDUPLATFORM                                │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Identity │  │  Course   │  │  Lesson   │  │  Search &    │  │
│  │ & Access │  │          │  │ & Content │  │  Discovery   │  │
│  │   ✅     │  │   ✅     │  │   ✅      │  │    ✅        │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │Enrollment│  │ Payments │  │ Progress  │  │Notifications │  │
│  │   ✅     │  │  ✅      │  │   ✅      │  │    ✅        │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │ Reviews  │  │ Teacher  │  │    AI     │  │  Learning    │  │
│  │& Ratings │  │  Tools   │  │  Service  │  │  Engine      │  │
│  │   ✅     │  │   ✅     │  │    ✅     │  │    ✅        │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
│  │Gamifica- │  │  Video   │  │ Analytics │  │   Social     │  │
│  │tion      │  │ Platform │  │  & Reco   │  │ & Community  │  │
│  │   ✅     │  │   🔴     │  │    🔴     │  │    🔴        │  │
│  └──────────┘  └──────────┘  └───────────┘  └──────────────┘  │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐                    │
│  │ Market-  │  │Enterprise│  │Integra-   │                    │
│  │ place    │  │ & Teams  │  │tions/SSO  │                    │
│  │   🔴     │  │   🔴     │  │    🔴     │                    │
│  └──────────┘  └──────────┘  └───────────┘                    │
└─────────────────────────────────────────────────────────────────┘

✅ = реализовано   🔴 = будущее (спринты 5–16)
```

---

## Домен 1: Identity & Access ✅

**Бизнес-цель:** Единая точка входа для студентов и преподавателей.

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 1.1 | Модель пользователя (student, teacher, admin) | P0 | ✅ |
| 1.2 | JWT auth (access token, role + is_verified в claims) | P0 | ✅ |
| 1.3 | Register, Login, GET /me | P0 | ✅ |
| 1.4 | Admin: list pending teachers, verify teacher | P0 | ✅ |
| 1.5 | Редактирование профиля (name, bio) | P2 | 🔴 |
| 1.6 | Password reset flow | P1 | ✅ |
| 1.7 | JWT refresh tokens (rotation + reuse detection) | P1 | ✅ |
| 1.8 | Social login (Google, Telegram) | P3 | 🔴 |
| 1.9 | Rate limiting и brute-force protection | P1 | ✅ |
| 1.10 | Email verification | P1 | ✅ |

**Сервис:** Identity (:8001)
**Владение данными:** users, refresh_tokens, verification_tokens

---

## Домен 2: Course ✅

**Бизнес-цель:** Преподаватели создают курсы. Каталог содержит 1M+ курсов.

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 2.1 | Модель курса: title, description, price, level, duration, avg_rating | P0 | ✅ |
| 2.2 | CRUD курсов с role-based access (only verified teachers) | P0 | ✅ |
| 2.3 | Поиск курсов (ILIKE + pg_trgm GIN index, p99 < 50ms) | P0 | ✅ |
| 2.4 | Редактирование курса (PUT /courses/:id) | P0 | ✅ |
| 2.5 | Категории курсов + фильтрация + сортировка | P1 | ✅ |
| 2.6 | Redis cache-aside (course by id, curriculum) | P1 | ✅ |
| 2.7 | Cursor-based pagination | P1 | ✅ |
| 2.8 | Image/thumbnail для курса | P3 | 🔴 |

**Сервис:** Course (:8002)
**Владение данными:** courses, modules, lessons, reviews, categories

---

## Домен 3: Lesson & Content ✅

**Бизнес-цель:** Структурированные уроки. Студент может учиться.

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 3.1 | Модель: Module + Lesson (markdown + video_url) | P0 | ✅ |
| 3.2 | CRUD модулей и уроков | P0 | ✅ |
| 3.3 | GET /courses/:id/curriculum | P0 | ✅ |
| 3.4 | GET /lessons/:id | P0 | ✅ |
| 3.5 | Загрузка видео-файлов | P3 | 🔴 |

**Сервис:** Course Service (:8002)

---

## Домен 4: Enrollment ✅

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 4.1 | POST /enrollments (student only) | P0 | ✅ |
| 4.2 | GET /enrollments/me | P0 | ✅ |
| 4.3 | GET /enrollments/course/:id/count | P0 | ✅ |
| 4.4 | Duplicate protection (UNIQUE) | P0 | ✅ |

**Сервис:** Enrollment (:8003)

---

## Домен 5: Progress & Completion ✅

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 5.1 | POST /progress/lessons/:id/complete | P0 | ✅ |
| 5.2 | GET /progress/courses/:id (% completion) | P0 | ✅ |
| 5.3 | GET /progress/courses/:id/lessons | P0 | ✅ |
| 5.4 | Auto-completion при 100% | P1 | ✅ |
| 5.5 | Сертификат по завершении (PDF) | P3 | 🔴 |

**Сервис:** Enrollment Service (:8003)

---

## Домен 6: Payments ✅

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 6.1 | POST /payments (mock, always completed) | P0 | ✅ |
| 6.2 | GET /payments/me, GET /payments/:id | P0 | ✅ |
| 6.3 | Stripe SDK adapter (backend) | P2 (Growth) | ✅ |
| 6.4 | Subscription plans + user_subscriptions (backend) | P2 (Growth) | ✅ |
| 6.5 | Teacher earnings + payouts (backend) | P2 (Growth) | ✅ |
| 6.6 | Stripe frontend (checkout, pricing) | P2 (Growth) | 🔴 sprint-3 |

**Сервис:** Payment (:8004)

---

## Домен 7: Notifications ✅

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 7.1 | POST, GET /me, PATCH /read | P0 | ✅ |
| 7.2 | FSRS review reminders | P1 (Phase 2.1) | ✅ |
| 7.3 | Streak at risk reminders | P1 (Phase 2.4) | ✅ |
| 7.4 | Email delivery (SMTP) | P2 (Growth) | 🔴 |

**Сервис:** Notification (:8005)

---

## Домен 8: Reviews & Ratings ✅

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 8.1 | POST /reviews (1-5 + comment) | P0 | ✅ |
| 8.2 | GET /reviews/course/:id | P0 | ✅ |
| 8.3 | Denormalized avg_rating, review_count | P0 | ✅ |
| 8.4 | UNIQUE per student per course | P0 | ✅ |

**Сервис:** Course Service (:8002)

---

## Домен 9: Search & Discovery ✅

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 9.1 | ILIKE + pg_trgm GIN index | P0 | ✅ |
| 9.2 | Фильтры: level, is_free, category | P1 | ✅ |
| 9.3 | Сортировка: created_at, avg_rating, price | P1 | ✅ |
| 9.4 | Meilisearch (full-text) | P3 (Scale) | 🔴 |

**Сервис:** Course Service (:8002)

---

## Домен 10: AI Service ✅ (Phase 2.0–2.2)

**Бизнес-цель:** Центральная точка LLM-взаимодействий. Model routing для оптимизации стоимости.

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 10.1 | Gemini Flash integration (httpx) | P0 | ✅ |
| 10.2 | Quiz generation из lesson content | P0 | ✅ |
| 10.3 | Lesson summary generation | P0 | ✅ |
| 10.4 | Socratic tutor pipeline | P1 | ✅ |
| 10.5 | Redis кэширование AI-ответов + conversation memory | P0 | ✅ |
| 10.6 | Plan-based AI credits (free/student/pro) | P1 | ✅ |

**Сервис:** AI Service (:8006)
**Владение данными:** prompt templates, AI response cache

---

## Домен 11: Learning Engine ✅ (Phase 2.0–2.4)

**Бизнес-цель:** "Мозг" платформы — адаптивные пути, spaced repetition, knowledge graph, gamification.

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 11.1 | Quiz model: questions, answers, attempts | P0 (Phase 2.0) | ✅ |
| 11.2 | FSRS scheduler (py-fsrs) | P0 (Phase 2.1) | ✅ |
| 11.3 | Flashcard model + review log | P0 (Phase 2.1) | ✅ |
| 11.4 | Concept model (knowledge points) + edges | P1 (Phase 2.3) | ✅ |
| 11.5 | Concept mastery tracking (per-student) | P1 (Phase 2.3) | ✅ |
| 11.6 | Adaptive pre-test | P1 (Phase 2.3) | ⏭️ YAGNI (sprint-10) |
| 11.7 | Learning velocity metrics | P1 (Phase 2.3) | ⏭️ YAGNI (sprint-10) |
| 11.8 | XP, streaks, badges, leaderboard, discussions | P1 (Phase 2.4) | ✅ |
| 11.9 | xAPI-style learning events (analytics) | P2 | 🔴 sprint-10 |

**Сервис:** Learning Engine (:8007)
**Владение данными:** quizzes, flashcards, concepts, concept_mastery, learning_events

---

## Домен 12: Gamification ✅ (Phase 2.4)

**Бизнес-цель:** Мотивация и привычка. Превратить обучение в ежедневную активность.

| # | Задача | Приоритет | Статус |
|---|--------|-----------|--------|
| 12.1 | XP system (lesson +10, quiz +20, flashcard +5) | P1 | ✅ |
| 12.2 | Streaks (daily activity tracking, midnight reset) | P1 | ✅ |
| 12.3 | Badges (first_enrollment, streak_7, quiz_ace, mastery_100) | P2 | ✅ |
| 12.4 | Leaderboard per course + global | P2 | ✅ |
| 12.5 | Course discussions (comments per lesson + upvotes) | P1 | ✅ |

**Реализация:** часть Learning Engine (:8007) — 30 endpoints, 11 таблиц, 107 тестов.

---

## Домены вне текущего этапа (Growth / Scale)

| Домен | Описание | Sprint | Статус |
|-------|----------|--------|--------|
| Seller Dashboard | Teacher analytics, revenue, payouts | sprint-2, sprint-6 | 🟡 scaffolded |
| Real Payments frontend | Stripe checkout, pricing page | sprint-3 | 🔴 |
| Social & Community | Study groups, peer review, mentorship | sprint-11 | 🔴 |
| Marketplace & Discovery | Recommendations, coupons, instructor marketplace | sprint-12 | 🔴 |
| Video Platform | Upload + transcode + HLS streaming | sprint-13 | 🔴 |
| Integrations & SSO | Google/GitHub SSO, Slack, LTI, webhooks | sprint-14 | 🔴 |
| Enterprise & Teams | Team accounts, admin dashboard, SCIM | sprint-15 | 🔴 |
| Scale Infrastructure | Rust gateway, NATS, DB replicas, K8s | sprint-16 | 🔴 |
| Analytics | ClickHouse, ML recommendations | sprint-10, sprint-12 | 🔴 |
| Moderation | AI content moderation, fraud | sprint-12 | 🔴 |

---

## Матрица событий между доменами

| Событие | Источник | Подписчики |
|---------|----------|-----------|
| `user.registered` | Identity | Notifications |
| `course.created` | Course | Notifications, Search |
| `enrollment.created` | Enrollment | Notifications, Learning Engine |
| `lesson.completed` | Progress | Enrollment, Learning Engine, Gamification |
| `quiz.submitted` | Learning Engine | Gamification (XP), FSRS (schedule review) |
| `flashcard.reviewed` | Learning Engine | Gamification (XP), FSRS (update schedule) |
| `concept.mastered` | Learning Engine | Gamification (badge), Adaptive Path |
| `streak.at_risk` | Gamification | Notifications |
| `payment.processed` | Payments | Enrollment, Notifications |
| `review.created` | Reviews | Course (avg_rating), Notifications |

> **Текущая реализация:** прямые вызовы. NATS JetStream — Phase Scale.
