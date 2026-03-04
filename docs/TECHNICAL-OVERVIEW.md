# EduPlatform — Technical Overview

B2B AI-powered engineering onboarding platform. Tri-Agent System (Strategist → Designer → Coach) генерирует персонализированные 15-минутные ежедневные миссии из реальной кодовой базы компании.

## Архитектура

Монорепа: Python (бизнес-логика, AI) + Next.js (frontend). Микросервисы с database-per-service. Пивот с B2C marketplace — Identity, AI, Learning, Notification сервисы переиспользуются, Course/Enrollment/Payment dormant.

```
                      ┌─────────────┐
                      │   Buyer     │
                      │  Next.js    │
                      │   :3001     │
                      └──────┬──────┘
                             │ /api proxy
        ┌────────┬───────────┼───────────┬──────────┐
        │        │           │           │          │
   ┌────▼──┐ ┌──▼───┐ ┌────▼────┐ ┌───▼────┐ ┌───▼──┐
   │Identit│ │  AI  │ │Learning │ │Notific.│ │ RAG  │
   │ :8001 │ │:8006 │ │ :8007   │ │ :8005  │ │:8008 │
   └───┬───┘ └──┬───┘ └───┬─────┘ └───┬────┘ └──┬───┘
       │        │         │           │          │
  ┌────▼──┐    Redis ┌───▼─────┐ ┌───▼────┐ ┌──▼────┐
  │ident. │         │learning │ │notif.  │ │rag-db │
  │  db   │         │  db     │ │  db    │ │pgvect.│
  │:5433  │         │ :5438   │ │ :5437  │ │:5439  │
  └───────┘         └─────────┘ └────────┘ └───────┘
```

## Стек

| Слой | Технология | Назначение |
|------|-----------|------------|
| Бизнес-логика | Python 3.12 / FastAPI | Clean Architecture, async |
| Frontend | Next.js 15 / Tailwind CSS 4 | App Router, TanStack Query |
| БД | PostgreSQL 16 | Database-per-service |
| Vector DB | PostgreSQL + pgvector | RAG embeddings, semantic search |
| Кэш | Redis 7 | Cache, rate limiting, AI conversation memory |
| AI / LLM | Gemini 2.0 Flash Lite | Tri-Agent System, quiz gen, tutor |
| Embeddings | Gemini text-embedding-004 | Document + code embeddings для RAG |
| Метрики | Prometheus + Grafana | RPS, latency, pool metrics |
| Пакеты | uv (Python), pnpm (JS) | Монорепа workspace |

## Сервисы

| Сервис | Порт | БД порт | Роль | Статус |
|--------|------|---------|------|--------|
| Identity | 8001 | 5433 | Auth, JWT, roles, orgs | ✅ Active |
| Course | 8002 | 5434 | CRUD курсов, search | ⏸ Dormant |
| Enrollment | 8003 | 5435 | Запись, прогресс | ⏸ Dormant |
| Payment | 8004 | 5436 | Платежи, subscriptions | ⏸ Dormant (реактивация в Sprint 22) |
| Notification | 8005 | 5437 | In-app, email, DMs | ✅ Active |
| AI | 8006 | — (Redis) | Tri-Agent System, LLM routing | ✅ Active |
| Learning | 8007 | 5438 | Quizzes, FSRS, knowledge graph, missions | ✅ Active |
| RAG | 8008 | 5439 | Document ingestion, semantic search, concept extraction | ✅ Active |

## Tri-Agent System

Три специализированных AI-агента, работающих последовательно:

| Agent | Роль | Input | Output |
|-------|------|-------|--------|
| **Strategist** | Анализ кодовой базы, определение learning path, адаптация пути | RAG org concepts + Learning mastery + LLM | Ordered concept path (cached in Redis 24h), next concept, adapted path (remedial/skip) |
| **Designer** | Генерация mission-контента из реального кода | Concept name + RAG search results + previous concepts | MissionBlueprint: reading content (~400w), 3 MCQ check questions, code case from real sources, 2 recap questions |
| **Coach** | Socratic dialog, review ответов, подсказки | Mission context + engineer answers | Feedback, hints, trust level recommendation |

Pipeline: `Strategist → Designer → Coach` (sequential, stateful).

## RAG Pipeline

```
GitHub repo / Docs / Wiki
    → Ingest (clone, parse, extract)
    → Chunk (code: function-level, docs: section-level)
    → Embed (OpenAI / local model → pgvector)
    → Search (semantic similarity + entity filter)
    → Extract (functions, classes, concepts, dependencies)
```

Хранение: PostgreSQL + pgvector (rag-db :5439). Scope: per-organization.

## Mission Engine

Ежедневные 15-минутные сессии, адаптированные под Trust Level инженера.

**Типы миссий:**

| Тип | Trust Level | Описание |
|-----|-------------|----------|
| code_reading | 0-1 | Чтение и понимание фрагмента кода |
| architecture_quiz | 1-2 | Вопросы по архитектуре системы |
| code_writing | 2-3 | Написание кода по спецификации |
| PR_review | 3-5 | Ревью реального pull request |

**Trust Levels (0-5):** Observer → Reader → Contributor → Developer → Reviewer → Expert. Прогрессия через completion rate, quiz scores, Coach оценки.

## Базы данных

| БД | Порт | Сервис | Таблицы |
|----|------|--------|---------|
| identity-db | 5433 | Identity | users, refresh_tokens, email_tokens, password_tokens, referrals, follows, organizations, org_members |
| course-db | 5434 | Course (dormant) | courses, modules, lessons, reviews, categories, bundles, wishlist |
| enrollment-db | 5435 | Enrollment (dormant) | enrollments, lesson_progress |
| payment-db | 5436 | Payment (dormant) | payments, subscription_plans, user_subscriptions, teacher_earnings, payouts, coupons, refunds, gifts |
| notification-db | 5437 | Notification | notifications, conversations, messages |
| learning-db | 5438 | Learning | quizzes, questions, quiz_attempts, flashcards, review_logs, concepts, concept_edges, concept_mastery, streaks, leaderboard_entries, discussions, xp_events, badges, user_badges, pretests, pretest_answers, activity_events, study_groups, study_group_members |
| rag-db | 5439 | RAG | documents, chunks (pgvector embeddings) |
| Redis | 6379 | All | Cache, rate limiting, AI memory, session |

## Тесты

```bash
cd services/py/identity    && uv run --package identity pytest tests/ -v     # 92 tests
cd services/py/course      && uv run --package course pytest tests/ -v       # 111 tests
cd services/py/enrollment  && uv run --package enrollment pytest tests/ -v   # 28 tests
cd services/py/payment     && uv run --package payment pytest tests/ -v      # 151 tests
cd services/py/notification && uv run --package notification pytest tests/ -v # 57 tests
cd services/py/ai          && uv run --package ai pytest tests/ -v           # 172 tests
cd services/py/learning    && uv run --package learning pytest tests/ -v     # 175 tests
cd services/py/rag         && uv run --package rag pytest tests/ -v          # 115 tests
```

**Итого:** 851 тестов по 8 сервисам.

## Инфраструктура

```bash
# Dev — hot reload
docker compose -f docker-compose.dev.yml up

# Seed data
docker compose -f docker-compose.dev.yml --profile seed up seed

# Prod — monitoring
docker compose -f docker-compose.prod.yml up -d

# Grafana → http://localhost:3000
# Prometheus → http://localhost:9090
# Locust → http://localhost:8089
```

## Порты

| Сервис | Порт |
|--------|------|
| Identity API | 8001 |
| Course API (dormant) | 8002 |
| Enrollment API (dormant) | 8003 |
| Payment API (dormant) | 8004 |
| Notification API | 8005 |
| AI API | 8006 |
| Learning API | 8007 |
| RAG API (Sprint 17) | 8008 |
| Buyer Frontend | 3001 |
| Seller Frontend (dormant) | 3002 |
| Grafana | 3000 |
| Prometheus | 9090 |
| Locust | 8089 |

## Frontend (Buyer App)

95+ endpoints на backend, растёт до 120+ с новыми сервисами.

Ключевые маршруты (текущие + планируемые):

| Route | Описание | Статус |
|-------|----------|--------|
| /courses | Каталог (dormant B2C) | ✅ |
| /courses/[id] | Детали курса (dormant B2C) | ✅ |
| /dashboard | Mission Dashboard (B2B) | 🔴 Sprint 21 |
| /coach | Coach Chat UI | 🔴 Sprint 21 |
| /knowledge | Knowledge Graph viz | 🔴 Sprint 21 |
| /admin | Team Analytics | 🔴 Sprint 22 |
| /settings/org | Org Switcher | 🔴 Sprint 21 |

## Текущий статус

| Sprint | Название | Задач | Статус |
|--------|----------|-------|--------|
| Pre-pivot | Foundation + Optimization + Learning Intelligence | — | ✅ Завершено |
| **Sprint 17** | RAG Foundation | 5 | 🔴 Следующий |
| **Sprint 18** | Tri-Agent System | 5 | 🔴 |
| **Sprint 19** | Mission Engine + Trust Levels | 6 | 🔴 |
| **Sprint 20** | Company Integration | 5 | 🔴 |
| **Sprint 21** | Frontend Redesign | 5 | 🔴 |
| **Sprint 22** | B2B Launch | 4 | 🔴 |

**Итого:** 30 задач в 6 спринтах для B2B MVP.

## Документация

| Документ | Описание |
|----------|----------|
| [Phase 0](docs/phases/PHASE-0-FOUNDATION.md) | Foundation (completed, pre-pivot) |
| [Phase 1](docs/phases/PHASE-1-LAUNCH.md) | Optimization (completed, pre-pivot) |
| [Phase 2](docs/phases/PHASE-2-LEARNING-INTELLIGENCE.md) | Learning Intelligence (completed, pre-pivot) |
| [Phase 3](docs/phases/PHASE-3-GROWTH.md) | B2B Sprint Roadmap (active, Sprints 17-22) |
| [Phase 4](docs/phases/PHASE-4-SCALE.md) | Scale & Enterprise (future) |
| [Architecture](docs/architecture/) | System overview, API reference, DB schemas |
