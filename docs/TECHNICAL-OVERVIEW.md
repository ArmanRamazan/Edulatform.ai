# EduPlatform — Technical Overview

Архитектурный справочник проекта: текущий статус, стек, структура, порты, быстрый старт.

## Текущий статус

**Стадия:** Phase 2.3 (Knowledge Graph + Concept Mastery) ✅ — 157 RPS, p99 51ms

| Компонент | Статус | Описание |
|-----------|--------|----------|
| Identity Service | ✅ Готов | Регистрация, логин, JWT refresh tokens, роли, admin, email verification, forgot password |
| Course Service | ✅ Готов | CRUD курсов, pg_trgm поиск, модули/уроки, отзывы, категории, фильтрация, XSS sanitization |
| Enrollment Service | ✅ Готов | Запись на курс, прогресс обучения, lesson completion, auto-completion |
| Payment Service | ✅ Готов | Mock-оплата, GET /me, GET /:id |
| Notification Service | ✅ Готов | In-app уведомления, mark as read |
| AI Service | ✅ Готов | Quiz generation, summary generation, Socratic AI tutor, Gemini Flash, Redis cache, credit tracking |
| Learning Engine | ✅ Готов | Quiz persistence, FSRS flashcards, spaced repetition, knowledge graph, course discussions (comments + upvotes), XP system, badges, 22 endpoints |
| Buyer Frontend | ✅ Готов | Next.js 15 — каталог, поиск, уроки, прогресс, admin, TanStack Query, error boundaries |
| Shared Library | ✅ Готов | Config, errors, security, database, health checks, rate limiting |
| Docker Compose | ✅ Готов | Dev (hot reload) + Prod (monitoring, graceful shutdown) |
| Prometheus + Grafana | ✅ Готов | RPS, latency p50/p95/p99, error rate, pool metrics |
| Seed Script | ✅ Готов | 50K users + 100K courses + 200K enrollments + 100K reviews |
| Locust | ✅ Готов | 3 сценария: Student (70%), Search (20%), Teacher (10%) |
| Unit Tests | ✅ 285 тестов | identity 48, course 59, enrollment 25, payment 13, notification 12, ai 30, learning 98 |

## Стек

| Слой | Технология | Почему |
|------|-----------|--------|
| Бизнес-логика | Python 3.12 / FastAPI | Быстрая разработка, Clean Architecture |
| Performance-critical | Rust (будет) | API gateway, поиск, видео — когда Python упрётся в потолок |
| Frontend | Next.js 15 / Tailwind CSS 4 | SSR/SSG, App Router, TanStack Query |
| БД | PostgreSQL 16 | Каждый сервис — своя БД |
| Кэш / Rate limit | Redis 7 | Course cache (TTL 5min), rate limiting (sliding window), все сервисы |
| AI / LLM | Gemini 2.0 Flash Lite (httpx) | Quiz gen, summary gen, Socratic tutor, credit tracking |
| Метрики | Prometheus + Grafana | Автоматические метрики через prometheus-fastapi-instrumentator |
| Нагрузка | Locust | Сценарии, имитирующие реальный трафик |
| Пакеты | uv (Python), npm (JS) | uv workspace для монорепы |

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
cd apps/buyer
npm install
npm run dev    # http://localhost:3001
```

### Тесты

```bash
# Установить зависимости (из корня)
uv sync --all-packages

# Все 7 сервисов (224 теста)
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
├── services/py/payment/     — Payment: mock-оплата
├── services/py/notification/— Notifications: in-app, mark as read
├── services/py/ai/          — AI: quiz gen, summary, Socratic tutor, Gemini Flash, Redis cache, credit tracking
├── services/py/learning/   — Learning Engine: quizzes, FSRS flashcards, knowledge graph, discussions
├── apps/buyer/              — Next.js frontend
├── deploy/docker/           — Dockerfiles, Prometheus, Grafana
├── tools/seed/              — Data generation (50K users, 100K courses, 200K enrollments)
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
| **Learning Intelligence** | 10K → 100K | AI-тьютор, квизы, spaced repetition, knowledge graph | 🟡 2.0–2.3 ✅, 2.4–2.5 🔴 |
| **Growth** | 100K → 1M | Реальные платежи, seller dashboard, SEO, mobile, CI/CD | 🔴 Не начато |
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
