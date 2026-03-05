# KnowledgeOS — Technical Overview

B2B AI-powered engineering onboarding platform. Tri-Agent System (Strategist → Designer → Coach) генерирует персонализированные 15-минутные ежедневные миссии из реальной кодовой базы компании.

## Архитектура

Монорепа: Python (бизнес-логика, AI) + Rust (performance-critical) + Next.js (frontend). Микросервисы с database-per-service. Пивот с B2C marketplace — Identity, AI, Learning, Notification сервисы переиспользуются, Course/Enrollment/Payment dormant. Rust Performance Layer (Sprints 23-25): API Gateway, Search, Embedding, WebSocket.

```
                      ┌─────────────┐
                      │   Buyer     │
                      │  Next.js    │
                      │   :3001     │
                      └──────┬──────┘
                             │
                      ┌──────▼──────┐     ┌───────────────────────┐
                      │ API Gateway │     │  RUST PERFORMANCE     │
                      │ Axum :8080  │────▶│  Search :8010         │
                      │ JWT, Rate   │     │  Embed :8009          │
                      │ Limit, CORS │     │  WS :8011             │
                      └──────┬──────┘     │  Chunker (pyo3 FFI)   │
                             │            └───────────────────────┘
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
| Frontend | Next.js 15 / Tailwind CSS 4 | App Router, TanStack Query, shadcn/ui (Dark Knowledge theme) |
| БД | PostgreSQL 16 | Database-per-service |
| Vector DB | PostgreSQL + pgvector | RAG embeddings, semantic search |
| Кэш | Redis 7 | Cache, rate limiting, AI conversation memory |
| AI / LLM | Gemini 2.0 Flash Lite | Tri-Agent System, quiz gen, tutor |
| Embeddings | Gemini text-embedding-004 | Document + code embeddings для RAG |
| Метрики | Prometheus + Grafana | RPS, latency, pool metrics |
| Performance Layer | Rust / Axum / Tokio | API Gateway, Search, Embedding, WebSocket |
| Search Engine | tantivy | Full-text search (replaces Meilisearch) |
| FFI Bridge | pyo3 + maturin | Rust chunker called from Python RAG |
| Пакеты | uv (Python), pnpm (JS), cargo (Rust) | Монорепа workspace |

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
| RAG | 8008 | 5439 | Document ingestion, semantic search, concept extraction, KB management | ✅ Active |

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
    → Ingest (clone, parse, extract) — GitHub adapter для repo ingestion
    → Chunk (code: function-level, docs: section-level)
    → Embed (Gemini text-embedding-004 → pgvector)
    → Search (semantic similarity + entity filter)
    → Extract (functions, classes, concepts, dependencies)
```

Хранение: PostgreSQL + pgvector (rag-db :5439). Scope: per-organization. GitHub adapter позволяет загружать репозитории напрямую.

## Rust Performance Layer

Sprints 23-25. Rust-сервисы для performance-critical paths:

| Сервис | Порт | Технологии | Назначение | Sprint |
|--------|------|-----------|------------|--------|
| API Gateway | 8080 | Axum, tower-http, jsonwebtoken, redis, reqwest, uuid, thiserror, tracing | Единая точка входа, JWT verification, Redis sliding window rate limiting, CORS (env-based origins), structured JSON request logging (X-Request-Id), reverse proxy routing to Python services | 23 (JWT + rate limit + proxy + CORS + logging done) |
| RAG Chunker | — (FFI) | pyo3, maturin | CPU-bound chunking из Python RAG | 24 |
| Search Service | 8010 | Axum, tantivy, tower-http, serde, thiserror | Full-text search (BM25), org-scoped indexing, batch index, snippet highlighting | Done (10 tests) |
| Embedding Orchestrator | 8009 | Axum, tokio, reqwest | Batch parallel embeddings | 25 |
| WebSocket Gateway | 8011 | Axum, tokio-tungstenite | Real-time Coach chat, notifications | 25 |

Критерий: p99 < 50ms или > 10K RPS → Rust. IO-bound бизнес-логика → Python.

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
| learning-db | 5438 | Learning | quizzes, questions, quiz_attempts, flashcards, review_logs, concepts, concept_edges, concept_mastery, streaks, leaderboard_entries, discussions, xp_events, badges, user_badges, pretests, pretest_answers, activity_events, study_groups, study_group_members, certificates, trust_levels, missions |
| rag-db | 5439 | RAG | documents, chunks (pgvector embeddings), org_concepts, concept_relationships |
| Redis | 6379 | All | Cache, rate limiting, AI memory, session |

## Тесты

```bash
cd services/py/identity    && uv run --package identity pytest tests/ -v     # 156 tests
cd services/py/course      && uv run --package course pytest tests/ -v       # 129 tests
cd services/py/enrollment  && uv run --package enrollment pytest tests/ -v   # 39 tests (+3 failing)
cd services/py/payment     && uv run --package payment pytest tests/ -v      # 181 tests
cd services/py/notification && uv run --package notification pytest tests/ -v # 136 tests (+3 failing)
cd services/py/ai          && uv run --package ai pytest tests/ -v           # 257 tests
cd services/py/learning    && uv run --package learning pytest tests/ -v     # 272 tests
cd services/py/rag         && uv run --package rag pytest tests/ -v          # 161 tests
```

**Итого (Python):** 1331 passed, 6 failing по 8 сервисам.

**Rust:**
```bash
cd services/rs/api-gateway && cargo test && cargo clippy -- -D warnings  # 39 tests
cd services/rs/search && cargo test && cargo clippy -- -D warnings       # 10 tests
```

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
| RAG API | 8008 |
| API Gateway (Rust/Axum) | 8080 |
| Embedding Orchestrator (Rust) | 8009 |
| Search Service (Rust/tantivy) | 8010 |
| WebSocket Gateway (Rust) | 8011 |
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
| /dashboard | Mission Dashboard — 7 endpoint-driven blocks | ✅ Built (Sprint 21) |
| /org/select | Organization Selector | ✅ Built (Sprint 21) |
| /graph | Knowledge Graph visualization | 🔴 Sprint 22 |
| /graph/[conceptId] | Concept detail view | 🔴 Sprint 22 |
| /search | Semantic search | 🔴 Sprint 22 |
| /missions/[id] | 5-phase Socratic mission session with coach chat | ✅ Built (Sprint 22) |
| /admin | Team Analytics | 🔴 Sprint 26 |

**Dark Knowledge Theme (Sprint 21):**
- UI: shadcn/ui (15 components), next-themes, framer-motion, lucide-react, cmdk
- Route groups: `(marketing)` для landing/auth, `(app)` для sidebar layout
- Layout: Sidebar + TopBar + CommandPalette (Cmd+K)
- Dashboard blocks: Greeting, Mission, TrustLevel, Flashcards, Mastery, Activity, TeamProgress
- OrgProvider + org selector для multi-tenant context

## Текущий статус

| Sprint | Название | Задач | Статус |
|--------|----------|-------|--------|
| Pre-pivot | Foundation + Optimization + Learning Intelligence | — | ✅ Завершено |
| **Sprint 17** | RAG Foundation | 5 | ✅ Done |
| **Sprint 18** | Tri-Agent System | 5 | ✅ Done |
| **Sprint 19** | Mission Engine + Trust Levels | 6 | ✅ Done |
| **Sprint 20** | Company Integration | 5 | ✅ Done |
| **Sprint 21** | Dark Knowledge Foundation | 5 | ✅ Done (shadcn/ui, sidebar, dashboard, org selector, GitHub adapter) |
| **Sprint 22** | Knowledge Platform UI | 4 | 🔴 Следующий |
| **Sprint 23-25** | Rust Performance Layer | 15 | 🔴 Planned |
| **Sprint 26** | B2B Admin | — | 🔴 Planned |
| **Sprint 27** | MCP Server | — | 🔴 Planned |

**Итого:** 30 задач B2B MVP + 15 задач Rust Performance Layer + B2B Admin + MCP.

## Документация

| Документ | Описание |
|----------|----------|
| [Phase 0](docs/phases/PHASE-0-FOUNDATION.md) | Foundation (completed, pre-pivot) |
| [Phase 1](docs/phases/PHASE-1-LAUNCH.md) | Optimization (completed, pre-pivot) |
| [Phase 2](docs/phases/PHASE-2-LEARNING-INTELLIGENCE.md) | Learning Intelligence (completed, pre-pivot) |
| [Phase 3](docs/phases/PHASE-3-GROWTH.md) | B2B Sprint Roadmap (active, Sprints 17-22) |
| [Phase 4](docs/phases/PHASE-4-SCALE.md) | Scale & Enterprise (future) |
| [Architecture](docs/architecture/) | System overview, API reference, DB schemas |
