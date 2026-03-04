# 01 — Обзор системы

> Последнее обновление: 2026-03-03
> Стадия: Phase 3.2 (Monetization backend — Stripe, subscriptions, earnings, payouts)

---

## Что есть сейчас

EduPlatform — учебная платформа с полным циклом обучения. Семь бэкенд-сервисов, один полноценный фронтенд (Buyer App) и инфраструктура мониторинга/нагрузочного тестирования. Три роли: Student, Teacher, Admin.

Студент может найти курс по категориям и фильтрам, записаться (включая платные курсы и подписки), пройти уроки, отслеживать прогресс (auto-completion при 100%), оставить отзыв, проходить квизы, повторять flashcards по FSRS, задавать вопросы AI-тьютору (Socratic method), видеть прогресс mastery по концептам курса, накапливать XP и badges, поддерживать streak, участвовать в leaderboard и обсуждениях.

Преподаватель может создать курс с модулями и уроками, создавать квизы, управлять knowledge graph (concepts + prerequisites), видеть аналитику по своему курсу (GET /analytics/teacher), получать выплаты (earnings, payouts).

Администратор верифицирует преподавателей, отправляет streak/flashcard reminders.

**Метрики:** 84 endpoint, 28 таблиц в 6 БД, 415 тестов, 157 RPS (p99 51ms).

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          КЛИЕНТЫ                                          │
│                                                                          │
│          Browser (http://localhost:3001)                                  │
│              │                                                           │
│              ▼                                                           │
│   ┌──────────────────┐      ┌──────────────────┐                        │
│   │   Buyer App      │      │   Seller App     │                        │
│   │   Next.js 15     │      │   Next.js 15     │                        │
│   │   TypeScript     │      │   (scaffolded,   │                        │
│   │   :3001          │      │    empty)        │                        │
│   │   18 routes      │      │                  │                        │
│   │   12 hooks       │      │                  │                        │
│   └────────┬─────────┘      └──────────────────┘                        │
│            │  /api proxy (next.config.ts rewrites)                       │
│            │                                                             │
├────────────┼─────────────────────────────────────────────────────────────┤
│            │                BACKEND SERVICES                              │
│            │                                                             │
│  ┌─────────┴──────────────────────────────────────────────────────────┐  │
│  │         │          │         │          │          │          │     │  │
│  ▼         ▼          ▼         ▼          ▼          ▼          ▼     │  │
│ ┌────────┐ ┌────────┐ ┌──────┐ ┌────────┐ ┌───────┐ ┌──────┐ ┌──────┐│  │
│ │Identity│ │ Course │ │Enrol-│ │Payment │ │Notif. │ │  AI  │ │Learn-││  │
│ │ :8001  │ │ :8002  │ │ment  │ │ :8004  │ │ :8005 │ │:8006 │ │ ing  ││  │
│ │ Python │ │ Python │ │:8003 │ │ Python │ │Python │ │Python│ │:8007 ││  │
│ │FastAPI │ │FastAPI │ │Python│ │FastAPI │ │FastAPI│ │FastA.│ │Python││  │
│ └───┬────┘ └───┬────┘ └──┬───┘ └───┬────┘ └───┬───┘ └──┬───┘ └──┬───┘│  │
│     │          │          │         │           │         │        │    │  │
├─────┼──────────┼──────────┼─────────┼───────────┼─────────┼────────┼────┤
│     │        DATA LAYER   │         │           │         │        │    │
│     │          │          │         │           │         │        │    │
│ ┌───▼──┐ ┌───▼──┐ ┌───▼──┐ ┌──────▼──┐ ┌───▼──┐        ┌───▼──┐  │
│ │iden- │ │cours-│ │enrol-│ │payment  │ │noti- │(Redis) │learn-│  │
│ │tity  │ │e db  │ │ment  │ │db :5436 │ │f. db │  only  │ing db│  │
│ │db    │ │:5434 │ │db    │ │Stripe + │ │:5437 │        │:5438 │  │
│ │:5433 │ │      │ │:5435 │ │subscr.  │ │      │        │      │  │
│ └──────┘ └──────┘ └──────┘ └─────────┘ └──────┘        └──────┘  │
│                                                                    │
│                    ┌──────────┐                                    │
│                    │  Redis   │  :6379 (cache, rate limiting,      │
│                    │          │   AI credits + conv. memory)       │
│                    └──────────┘                                    │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                        OBSERVABILITY                                │
│                                                                    │
│   ┌────────────┐    ┌────────────┐    ┌────────────┐              │
│   │ Prometheus │───▶│  Grafana   │    │   Locust   │              │
│   │   :9090    │    │   :3000    │    │   :8089    │              │
│   └────────────┘    └────────────┘    └────────────┘              │
└────────────────────────────────────────────────────────────────────┘
```

---

## Порты

| Сервис | Порт | Протокол |
|--------|------|----------|
| Identity API | 8001 | HTTP/REST |
| Course API | 8002 | HTTP/REST |
| Enrollment API | 8003 | HTTP/REST |
| Payment API | 8004 | HTTP/REST |
| Notification API | 8005 | HTTP/REST |
| AI Service API | 8006 | HTTP/REST |
| Learning Engine API | 8007 | HTTP/REST |
| Buyer Frontend | 3001 | HTTP |
| Seller Frontend | 3002 | HTTP |
| Identity DB (PostgreSQL) | 5433 | TCP |
| Course DB (PostgreSQL) | 5434 | TCP |
| Enrollment DB (PostgreSQL) | 5435 | TCP |
| Payment DB (PostgreSQL) | 5436 | TCP |
| Notification DB (PostgreSQL) | 5437 | TCP |
| Learning DB (PostgreSQL) | 5438 | TCP |
| Redis | 6379 | TCP |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |
| Locust | 8089 | HTTP |

---

## Сервисы — описание

| Сервис | Endpoints | Таблиц | Тестов | Ключевые возможности |
|--------|-----------|--------|--------|----------------------|
| Identity | 11 | 2 | 52 | register, login, /me, roles (student/teacher/admin), email verification, forgot password, refresh tokens, teacher verification |
| Course | 17 | 4 | 71 | CRUD courses + modules + lessons + reviews, ILIKE search, curriculum, categories, filtering/sorting, GET /analytics/teacher |
| Enrollment | 6 | 3 | 28 | POST /enrollments, GET /me, lesson progress, auto-completion, course enrollment count |
| Payment | 7 | 4 | 61 | POST /payments (Stripe mock), subscription_plans, user_subscriptions, teacher_earnings, payouts, GET /me |
| Notification | 6 | 2 | 38 | POST (log to stdout), GET /me, PATCH /:id/read, POST /streak-reminders/send (admin), POST /flashcard-reminders/send (admin), POST /flashcard-reminders/smart (admin, FSRS-based) |
| AI Service | 5 | — | 49 | POST /ai/quiz/generate, POST /ai/summary/generate, POST /ai/tutor/chat, POST /ai/tutor/feedback, GET /ai/credits/me; Gemini Flash, plan-based credits (free:10/day, student:100/day, pro:unlimited), Redis conv. memory |
| Learning Engine | 33 | 13 | 126 | Quizzes (4), Flashcards+FSRS (4), Concepts/Knowledge Graph (7), Streaks (2), Leaderboard (5), Discussions (5), XP (1), Badges (1), Adaptive Pre-test (3) |

**Итого:** 84 endpoint, 28 таблиц, 415 тестов

---

## Стек технологий

| Слой | Технология | Версия | Зачем |
|------|-----------|--------|-------|
| Backend | Python / FastAPI | 3.12 / 0.115+ | Бизнес-логика, Clean Architecture |
| Frontend | Next.js / React / TanStack Query | 15.3 / 19.1 / 5.x | SSR/SSG, App Router, optimistic updates |
| Стили | Tailwind CSS | 4.1 | Утилитарные стили |
| UI примитивы | Radix UI | — | Headless accessible компоненты |
| БД | PostgreSQL | 16 (Alpine) | Database-per-service (6 инстансов) |
| Кэш / Rate limit | Redis | 7 (Alpine) | Course cache (TTL 5min), rate limiting (sliding window), AI credits + conversation memory |
| ORM | asyncpg | 0.30+ | Raw SQL, parameterized queries |
| Auth | PyJWT + bcrypt | 2.10+ / 4.0+ | JWT HS256, bcrypt хэширование |
| AI | Gemini Flash (Google) | — | Quiz generation, summary, Socratic tutor, feedback |
| Config | pydantic-settings | 2.7+ | Env vars → typed settings |
| Метрики | prometheus-fastapi-instrumentator | 7.0+ | Автоматические HTTP метрики |
| Monitoring | Prometheus + Grafana | — | Scrape 5s, dashboards |
| Load testing | Locust | — | StudentUser, SearchUser, TeacherUser |
| Seed | asyncpg + Faker | — | 1 admin + 50K users, 100K courses, ~210K lessons, 100K reviews, 50K payments, 200K enrollments, learning/gamification data |
| Packages | uv workspace | — | Python монорепа |
| Docker | Docker Compose | — | Dev (hot reload) + Prod (monitoring) |

---

## Buyer App — маршруты и возможности

**18 маршрутов**, 12 хуков TanStack Query, полноценный SSR/Client mix:

| Группа | Маршруты |
|--------|---------|
| Публичные | `/` (landing), `/courses/[id]` (карточка курса) |
| Авторизация | `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password` |
| Личный кабинет | `/my-courses`, `/enrollments`, `/notifications` |
| Обучение | `/courses/[id]/lessons/[lessonId]`, `/courses/[id]/edit`, `/courses/new` |
| Геймификация | `/flashcards`, `/badges`, `/courses/[id]/concepts` |
| Onboarding | `/onboarding` — guided first course experience |
| Администрирование | `/admin/teachers` — верификация преподавателей |

---

## Принципы архитектуры (реализованные)

1. **Database-per-service** — у каждого сервиса своя PostgreSQL (6 БД; AI Service stateless — только Redis cache)
2. **Clean Architecture** — routes → services → domain ← repositories
3. **JWT shared secret** — все 7 сервисов валидируют JWT самостоятельно, без обращения к Identity
4. **Клиент-оркестратор** — Frontend оркестрирует вызовы между сервисами (Payment → Enrollment → Notification)
5. **Роли в JWT claims** — `role` (student/teacher/admin), `is_verified` и `email_verified` в extra_claims
6. **Forward-only миграции** — SQL файлы, выполняются при старте сервиса, идемпотентны
7. **Owner check** — teacher управляет только своими курсами/модулями/уроками/quizzes (проверка teacher_id)
8. **Redis everywhere** — все 7 сервисов подключены к Redis (rate limiting + cache + AI credits)
9. **Health checks** — `/health/live` (liveness) + `/health/ready` (readiness) на всех 7 сервисах
10. **Refresh token rotation** — JWT access (1h) + refresh (30d) с family-based reuse detection
11. **Plan-based credits** — AI Service ограничивает использование Gemini по плану подписки (free/student/pro)

---

## Что оптимизировано (Phase 1.0–1.2)

| Оптимизация | Было | Стало |
|-------------|------|-------|
| pg_trgm GIN index на courses | search p99 = 803ms | search p99 = 35ms (23x) |
| Connection pool 5 → 5/20 (min/max) | 100% saturation | 10% saturation |
| Redis cache-aside (course, curriculum) | — | TTL 5 min, cache hit |
| FK indexes (11 новых) | full table scan на JOIN | index scan |
| Cursor pagination (keyset) | offset scan | constant time |
| Health checks (/health/live, /health/ready) | — | все 7 сервисов |
| Rate limiting (Redis sliding window) | — | 100/min global, 10/min login, 5/min register |
| CORS middleware | — | env-based origins |
| XSS sanitization (bleach) | — | course/lesson content |
| JWT refresh tokens | 1h access only | access (1h) + refresh (30d) + rotation |
| Graceful shutdown | — | timeout-graceful-shutdown 25s (prod) |

---

## Статус фаз

| Фаза | Статус | Что сделано |
|------|--------|-------------|
| Phase 0 | ✅ DONE | Фундамент: все 7 сервисов, БД, Docker, базовые endpoints |
| Phase 1 | ✅ DONE | Performance (pg_trgm, pool, Redis cache), Security (rate limit, CORS, XSS, JWT refresh), UX (categories, search, pagination) |
| Phase 2.0 | ✅ DONE | Enrollment + Payment (mock) + Notification |
| Phase 2.1 | ✅ DONE | Lesson progress + auto-completion |
| Phase 2.2 | ✅ DONE | AI Service — quiz gen, summary, Socratic tutor (Gemini Flash) |
| Phase 2.3 | ✅ DONE | Knowledge Graph — concepts, prerequisites, mastery tracking |
| Phase 2.4 | ✅ DONE | Gamification — XP, badges, streaks, leaderboard, discussions; Buyer App полный UI |
| Phase 2.5 | 🟡 PARTIAL | Часть сделана; onboarding, landing redesign, mobile — не завершены |
| Phase 3.1 | ✅ DONE (backend) | Stripe integration, subscription_plans, user_subscriptions — backend |
| Phase 3.2 | ✅ DONE (backend) | Teacher earnings, payouts, course analytics — backend |
| Phase 3.1–3.2 | 🔴 NOT DONE | Frontend для монетизации (seller dashboard, subscription UI) |
| Phase 3.3–3.5 | 🔴 NOT DONE | SEO/performance, CI/CD, engagement features |

---

## Чего нет (намеренно, YAGNI)

| Чего нет | Почему | Когда появится |
|----------|--------|---------------|
| API Gateway | Не нужен при прямом доступе к сервисам | Phase 3+ (Rust/Axum) |
| Event bus (NATS) | Нет межсервисных событий, клиент оркестрирует | Phase 3+ |
| CI/CD pipeline | Локальная разработка | Phase 3.4 |
| Kubernetes | Docker Compose достаточно | Phase 3.5+ |
| Proto/gRPC контракты | Прямые HTTP вызовы между сервисами не нужны пока | Phase 3+ |
| Seller App (полный) | Scaffolded, API client + auth | Phase 3.2 frontend (pages) |
| Email отправка (SMTP) | Stub — логирование в stdout | Phase 2+ |
| Video processing | Нет видео-контента | Phase 3+ |
