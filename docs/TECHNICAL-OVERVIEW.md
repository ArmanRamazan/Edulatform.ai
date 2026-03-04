# EduPlatform — Technical Overview

Архитектурный справочник проекта: текущий статус, стек, структура, порты, быстрый старт.

## Текущий статус

**Стадия:** Phase 2.4 ✅ (Gamification) — Phase 2.5 в процессе — Phase 3.1–3.2 backend ✅ — 157 RPS, p99 51ms

| Компонент | Статус | Описание |
|-----------|--------|----------|
| Identity Service | ✅ Готов | Регистрация, логин, JWT refresh tokens, роли, admin, email verification, forgot password |
| Course Service | ✅ Готов | CRUD курсов, pg_trgm поиск, модули/уроки, отзывы, категории, фильтрация, XSS sanitization |
| Enrollment Service | ✅ Готов | Запись на курс, прогресс обучения, lesson completion, auto-completion |
| Payment Service | ✅ Готов | Mock-оплата, Stripe SDK adapter, subscription_plans + user_subscriptions, teacher_earnings, payouts, GET /me, GET /:id, GET /earnings/me, POST /payouts/request |
| Notification Service | ✅ Готов | In-app уведомления, mark as read, streak-at-risk reminders, flashcard-due reminders |
| AI Service | ✅ Готов | Quiz generation, summary generation, Socratic AI tutor, course outline generation (teacher/admin), lesson content generation (teacher/admin), personalized study plan generation, Gemini Flash, Redis cache, plan-based credit system (free/student/pro tiers), service-to-service calls to Learning Service, GET /ai/credits/me |
| Learning Engine | ✅ Готов | Quiz persistence, FSRS flashcards, spaced repetition, knowledge graph, course discussions (comments + upvotes), XP system, badges, streaks, leaderboard, adaptive pre-test, learning velocity, 33 endpoints |
| Buyer Frontend | ✅ Готов | Next.js 15 — каталог, поиск, уроки, прогресс, admin, TanStack Query, error boundaries |
| Shared Library | ✅ Готов | Config, errors, security, database, health checks, rate limiting |
| Docker Compose | ✅ Готов | Dev (hot reload) + Prod (monitoring, graceful shutdown) |
| Prometheus + Grafana | ✅ Готов | RPS, latency p50/p95/p99, error rate, pool metrics |
| Seed Script | ✅ Готов | 50K users + 100K courses + 200K enrollments + 100K reviews + learning data (quizzes, concepts, flashcards, XP, badges, streaks, leaderboard, comments) |
| Locust | ✅ Готов | 3 сценария: Student (70%), Search (20%), Teacher (10%) |
| Unit Tests | ✅ 472 тестов | identity 52, course 71, enrollment 28, payment 61, notification 32, ai 95, learning 137 (incl. pre-test: 20, velocity: 11) |

## Стек

| Слой | Технология | Почему |
|------|-----------|--------|
| Бизнес-логика | Python 3.12 / FastAPI | Быстрая разработка, Clean Architecture |
| Performance-critical | Rust (будет) | API gateway, поиск, видео — когда Python упрётся в потолок |
| Frontend | Next.js 15 / Tailwind CSS 4 | SSR/SSG, App Router, TanStack Query |
| БД | PostgreSQL 16 | Каждый сервис — своя БД |
| Кэш / Rate limit | Redis 7 | Course cache (TTL 5min), rate limiting (sliding window), все сервисы |
| AI / LLM | Gemini 2.0 Flash Lite (httpx) | Quiz gen, summary gen, Socratic tutor, credit tracking |
| Логирование | structlog (JSON) | Structured logging, JSON в prod, console в dev |
| Метрики | Prometheus + Grafana | Автоматические метрики через prometheus-fastapi-instrumentator |
| Нагрузка | Locust | Сценарии, имитирующие реальный трафик |
| Пакеты | uv (Python), pnpm (JS) | uv workspace для монорепы |

## Быстрый старт

### Бэкенд (Docker)

```bash
# Dev — hot reload, volume mounts
docker compose -f docker-compose.dev.yml up

# Засеять данные (50K users + 100K courses)
docker compose -f docker-compose.dev.yml --profile seed up seed
```

### Фронтенд

```bash
cd apps/buyer && pnpm install && pnpm dev    # http://localhost:3001
cd apps/seller && pnpm install && pnpm dev   # http://localhost:3002
```

### Тесты

```bash
# Установить зависимости (из корня)
uv sync --all-packages

# Все 7 сервисов (487 тестов)
cd services/py/identity && uv run --package identity pytest tests/ -v
cd services/py/course && uv run --package course pytest tests/ -v
cd services/py/enrollment && uv run --package enrollment pytest tests/ -v
cd services/py/payment && uv run --package payment pytest tests/ -v
cd services/py/notification && uv run --package notification pytest tests/ -v
cd services/py/ai && uv run --package ai pytest tests/ -v
cd services/py/learning && uv run --package learning pytest tests/ -v
```

### Нагрузочное тестирование

```bash
# Prod stack + monitoring
docker compose -f docker-compose.prod.yml up -d

# Locust UI → http://localhost:8089
docker compose -f docker-compose.prod.yml --profile loadtest up locust

# Grafana → http://localhost:3000
```

## Порты

| Сервис | Порт |
|--------|------|
| Identity API | 8001 |
| Course API | 8002 |
| Enrollment API | 8003 |
| Payment API | 8004 |
| Notification API | 8005 |
| AI API | 8006 |
| Learning API | 8007 |
| Buyer Frontend | 3001 |
| Seller Frontend | 3002 |
| Grafana | 3000 |
| Prometheus | 9090 |
| Locust | 8089 |
| Identity DB (Postgres) | 5433 |
| Course DB (Postgres) | 5434 |
| Enrollment DB (Postgres) | 5435 |
| Payment DB (Postgres) | 5436 |
| Notification DB (Postgres) | 5437 |
| Learning DB (Postgres) | 5438 |
| Redis | 6379 |

## Структура

```
├── libs/py/common/          — Shared: config, errors, security, database, health, rate limiting
├── services/py/identity/    — Auth: register, login, JWT refresh tokens, roles, admin, email verification
├── services/py/course/      — Courses: CRUD, search, modules, lessons, reviews, categories, filtering
├── services/py/enrollment/  — Enrollment: запись на курс, прогресс, lesson completion, auto-completion
├── services/py/payment/     — Payment: mock-оплата, teacher earnings, payouts
├── services/py/notification/— Notifications: in-app, mark as read
├── services/py/ai/          — AI: quiz gen, summary, Socratic tutor, study plan, Gemini Flash, Redis cache, credit tracking
├── services/py/learning/   — Learning Engine: quizzes, FSRS flashcards, knowledge graph, discussions
├── apps/buyer/              — Next.js student frontend
├── apps/seller/             — Next.js teacher dashboard
├── deploy/docker/           — Dockerfiles, Prometheus, Grafana
├── tools/seed/              — Data generation (50K users, 100K courses, 200K enrollments, learning data)
├── tools/locust/            — Load test scenarios
├── tools/orchestrator/      — AI orchestrator: autonomous Claude Code executor for phase roadmap
├── docs/goals/              — Architecture decisions, domain specs
├── docs/architecture/       — Current system state (source of truth)
└── docs/phases/             — Implementation roadmap
```

## Roadmap

Подробный roadmap: [docs/goals/00-ROADMAP.md](docs/goals/00-ROADMAP.md)

| Стадия | Пользователи | Ключевые изменения | Статус |
|--------|-------------|-------------------|--------|
| **Foundation** | до 10K | 7 Python сервисов, Next.js, Postgres, Locust | ✅ Готово |
| **Learning Intelligence** | 10K → 100K | AI-тьютор, квизы, spaced repetition, knowledge graph, gamification | 🟡 2.0–2.4 ✅, 2.5 🔴 в процессе |
| **Growth** | 100K → 1M | Реальные платежи, seller dashboard, SEO, mobile, CI/CD | 🟡 3.1–3.2 backend ✅, frontend 🔴 |
| **Scale** | 1M → 10M | Rust gateway, event bus, video platform, multi-region | 🔴 Не начато |

## Документация

| Документ | Описание |
|----------|----------|
| [Видение продукта](docs/goals/01-PRODUCT-VISION.md) | Learning Velocity Engine, core loop, метрики |
| [Архитектура](docs/goals/02-ARCHITECTURE-PRINCIPLES.md) | ADR, принципы, выбор технологий |
| [Домены](docs/goals/04-DOMAINS.md) | Bounded contexts, event matrix |
| [Безопасность](docs/goals/06-SECURITY.md) | Threat model, mitigation |
| [Observability](docs/goals/09-OBSERVABILITY.md) | SLO, метрики, алерты |
| [Frontend](docs/goals/10-FRONTEND.md) | Next.js архитектура, performance budgets |
