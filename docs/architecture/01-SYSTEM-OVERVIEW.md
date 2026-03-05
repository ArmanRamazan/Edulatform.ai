# 01 — Обзор системы

> Последнее обновление: 2026-03-05
> Стадия: B2B Agentic Adaptive Learning Pivot

---

## Что есть сейчас

EduPlatform — B2B AI-powered платформа адаптивного онбординга инженеров. Tri-Agent System (Strategist → Designer → Coach) генерирует персонализированные 15-минутные ежедневные миссии на основе кодовой базы и документации компании. RAG-сервис индексирует репозитории и документы организации. Trust Levels (0–5) управляют прогрессивным доступом к ресурсам.

Шесть активных бэкенд-сервисов, один фронтенд (Buyer App, переработанный под B2B), инфраструктура мониторинга. Два сервиса (Course, Enrollment) в спящем режиме — код сохранён, но не развивается.

Мультитенантность: организации (organizations) с membership. JWT содержит `organization_id` для контекста активной организации.

**Метрики:** ~134 endpoints, ~49 таблиц в 7 БД, ~948 тестов.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          КЛИЕНТЫ                                        │
│                                                                         │
│          Browser (http://localhost:3001)                                 │
│              │                                                          │
│              ▼                                                          │
│   ┌──────────────────┐      ┌──────────────────┐                       │
│   │   Buyer App      │      │   Seller App     │                       │
│   │   Next.js 15     │      │   (dormant)      │                       │
│   │   TypeScript     │      │   :3002           │                       │
│   │   :3001          │      │                   │                       │
│   │   B2B Dashboard  │      │                   │                       │
│   │   Missions, KB   │      │                   │                       │
│   └────────┬─────────┘      └───────────────────┘                      │
│            │  /api proxy (next.config.ts rewrites)                      │
│            │                                                            │
│            ▼                                                            │
│  ┌──────────────────┐  ┌─────────────────────────────────────────┐     │
│  │  API Gateway     │  │       RUST PERFORMANCE LAYER            │     │
│  │  Axum :8080      │─▶│ Search :8010 │ Embed :8009 │ WS :8011  │     │
│  │  JWT, Rate Limit │  │ tantivy FTS  │ (planned)   │ (planned) │     │
│  │  CORS, ReqLogger │  │ RAG Chunker (pyo3 FFI, no port)        │     │
│  └────────┬─────────┘  └─────────────────────────────────────────┘     │
│                                                                        │
├────────────┼────────────────────────────────────────────────────────────┤
│            │              ACTIVE BACKEND SERVICES                       │
│            │                                                            │
│  ┌─────────┴───────────────────────────────────────────────────────┐   │
│  │         │          │          │          │          │            │   │
│  ▼         ▼          ▼          ▼          ▼          ▼            │   │
│ ┌────────┐ ┌────────┐ ┌───────┐ ┌──────┐ ┌────────┐ ┌──────────┐  │   │
│ │Identity│ │Payment │ │Notif. │ │  AI  │ │Learn-  │ │   RAG    │  │   │
│ │ :8001  │ │ :8004  │ │ :8005 │ │:8006 │ │ ing    │ │  :8008   │  │   │
│ │ Python │ │ Python │ │Python │ │Python│ │ :8007  │ │  Python  │  │   │
│ │FastAPI │ │FastAPI │ │FastAPI│ │FastA.│ │ Python │ │  FastAPI │  │   │
│ │        │ │        │ │       │ │      │ │ FastAPI│ │  pgvector│  │   │
│ └───┬────┘ └───┬────┘ └──┬───┘ └──┬───┘ └───┬───┘ └────┬─────┘  │   │
│     │          │          │        │          │          │         │   │
├─────┼──────────┼──────────┼────────┼──────────┼──────────┼─────────┤   │
│     │        DATA LAYER   │        │          │          │         │   │
│     │          │          │        │          │          │         │   │
│ ┌───▼──┐ ┌───▼───┐ ┌───▼──┐     │     ┌───▼──┐  ┌───▼──┐      │   │
│ │iden- │ │payment│ │noti- │  (Redis)  │learn-│  │rag   │      │   │
│ │tity  │ │db     │ │f. db │   only    │ing db│  │db    │      │   │
│ │db    │ │:5436  │ │:5437 │           │:5438 │  │:5439 │      │   │
│ │:5433 │ │       │ │      │           │      │  │pgvec.│      │   │
│ └──────┘ └───────┘ └──────┘           └──────┘  └──────┘      │   │
│                                                                    │
│          ┌──────────┐                                              │
│          │  Redis   │  :6379 (cache, rate limiting,                │
│          │          │   AI credits, agent memory, conv. memory)    │
│          └──────────┘                                              │
│                                                                    │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  DORMANT SERVICES (code preserved, not actively developed)  │  │
│  │  Course :8002 (course-db :5434)                             │  │
│  │  Enrollment :8003 (enrollment-db :5435)                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│                        OBSERVABILITY                               │
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
| Course API (dormant) | 8002 | HTTP/REST |
| Enrollment API (dormant) | 8003 | HTTP/REST |
| Payment API | 8004 | HTTP/REST |
| Notification API | 8005 | HTTP/REST |
| AI Service API | 8006 | HTTP/REST |
| Learning Engine API | 8007 | HTTP/REST |
| RAG Service API | 8008 | HTTP/REST |
| API Gateway (Rust/Axum) | 8080 | HTTP/REST |
| Embedding Orchestrator (Rust) | 8009 | HTTP/REST |
| Search Service (Rust/Axum/tantivy) | 8010 | HTTP/REST |
| WebSocket Gateway (Rust) | 8011 | WebSocket |
| Buyer Frontend | 3001 | HTTP |
| Seller Frontend (dormant) | 3002 | HTTP |
| Identity DB (PostgreSQL) | 5433 | TCP |
| Course DB (dormant) | 5434 | TCP |
| Enrollment DB (dormant) | 5435 | TCP |
| Payment DB (PostgreSQL) | 5436 | TCP |
| Notification DB (PostgreSQL) | 5437 | TCP |
| Learning DB (PostgreSQL) | 5438 | TCP |
| RAG DB (PostgreSQL + pgvector) | 5439 | TCP |
| Redis | 6379 | TCP |
| Prometheus | 9090 | HTTP |
| Grafana | 3000 | HTTP |
| Locust | 8089 | HTTP |

---

## Сервисы — описание

### Активные сервисы

| Сервис | Endpoints | Таблиц | Тестов | Ключевые возможности |
|--------|-----------|--------|--------|----------------------|
| Identity | ~33 | 8 | 156 | register, login, /me, roles, email verification, forgot password, refresh tokens, teacher verification, referrals, public profiles, follows, **organizations**, **org members** |
| Payment | ~25 | 10 | 151 | POST /payments (Stripe mock), subscription_plans, user_subscriptions, teacher_earnings, payouts, coupons, invoice PDF, refunds, gifts, **org_subscriptions** |
| Notification | ~9 | 3 | 57 | POST (email stub), GET /me, PATCH read, streak/flashcard reminders, direct messaging (conversations + messages) |
| AI Service | ~21 | — | 207 | quiz/summary generation, Socratic tutor, study-plan, content moderation, **Strategist** (path planning via LLM + RAG concepts + Learning mastery, next concept, adaptive path with remedial/skip, Redis cache 24h), **Designer** (mission generation, recaps), **Coach** (guided sessions), **daily mission**, **agent memory**, **configurable LLM provider per org** (Gemini/self-hosted OpenAI-compatible, data isolation) |
| Learning Engine | ~55 | 21 | 265 | Quizzes, Flashcards+FSRS, Concepts/Knowledge Graph, Streaks, Leaderboard, Discussions, XP, Badges, Pre-tests, Velocity, Activity Feed, Study Groups, Certificates, **Missions** (daily, streak, completion), **Trust Levels**, **Daily summary** |
| RAG Service | ~20 | 6 | 115 | Document ingestion (markdown, GitHub), pgvector semantic search, LLM concept extraction (auto-extraction in pipeline), knowledge base management, onboarding templates with stages |

**Итого (активные):** ~154 endpoints, ~48 таблиц, ~806 тестов

### Спящие сервисы (dormant)

| Сервис | Endpoints | Таблиц | Тестов | Статус |
|--------|-----------|--------|--------|--------|
| Course | 17 | 9 | 111 | Код сохранён, не развивается |
| Enrollment | 8 | 2 | 28 | Код сохранён, не развивается |

---

## Межсервисное взаимодействие

```
AI Service ──HTTP──▶ Learning Engine     (concept mastery, mission status)
AI Service ──HTTP──▶ RAG Service         (semantic search, concept graph)
Notification ──HTTP──▶ Learning Engine   (smart flashcard reminders)
Frontend (Buyer) orchestrates:
  Identity → AI → Learning → RAG → Payment → Notification
```

Все межсервисные вызовы — HTTP REST. Клиент (Buyer App) является основным оркестратором. AI Service обращается к Learning и RAG напрямую для агентного пайплайна.

---

## Стек технологий

| Слой | Технология | Версия | Зачем |
|------|-----------|--------|-------|
| Backend | Python / FastAPI | 3.12 / 0.115+ | Бизнес-логика, Clean Architecture |
| Frontend | Next.js / React / TanStack Query | 15.3 / 19.1 / 5.x | SSR/SSG, App Router, optimistic updates |
| Стили | Tailwind CSS | 4.1 | Утилитарные стили |
| UI примитивы | Radix UI | — | Headless accessible компоненты |
| БД | PostgreSQL | 16 (Alpine) | Database-per-service (7 инстансов, 5 активных + 2 dormant) |
| Векторный поиск | pgvector | 0.7+ | Embedding-based semantic search (RAG DB) |
| Кэш / Rate limit | Redis | 7 (Alpine) | Cache, rate limiting, AI credits, agent memory, conversation memory |
| ORM | asyncpg | 0.30+ | Raw SQL, parameterized queries |
| Auth | PyJWT + bcrypt | 2.10+ / 4.0+ | JWT HS256, bcrypt хэширование |
| AI | Gemini Flash (Google) | — | Tri-Agent System (Strategist/Designer/Coach), quiz gen, summary, tutor |
| Embeddings | Gemini Embedding | — | Document/chunk embeddings для RAG |
| Config | pydantic-settings | 2.7+ | Env vars → typed settings |
| Метрики | prometheus-fastapi-instrumentator | 7.0+ | Автоматические HTTP метрики |
| Monitoring | Prometheus + Grafana | — | Scrape 5s, dashboards |
| Load testing | Locust | — | StudentUser, SearchUser, TeacherUser |
| Packages | uv workspace | — | Python монорепа |
| Performance Layer | Rust / Axum / Tokio | — | API Gateway, Search, Embedding, WebSocket |
| Search Engine | tantivy | — | Full-text search (replaces Meilisearch) |
| FFI Bridge | pyo3 + maturin | — | Rust chunker called from Python RAG |
| Docker | Docker Compose | — | Dev (hot reload) + Prod (monitoring) |

---

## Buyer App — маршруты и возможности

Переработан под B2B Agentic Adaptive Learning:

| Группа | Маршруты |
|--------|---------|
| Публичные | `/` (landing), `/login`, `/register` |
| Авторизация | `/verify-email`, `/forgot-password`, `/reset-password` |
| Dashboard | `/dashboard` — daily mission, progress overview, trust level |
| Миссии | `/mission` — текущая миссия, Coach chat, mission completion |
| Knowledge Base | `/knowledge` — org documents, concepts, search |
| Прогресс | `/progress` — mastery graph, velocity, streaks, badges, XP |
| Администрирование | `/admin/teachers` — верификация, `/admin` — org management |
| Биллинг | `/billing` — org subscription management |
| Onboarding | `/onboarding` — guided first experience, org setup |

---

## Ключевая концепция: Tri-Agent System

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Strategist │────▶│  Designer   │────▶│   Coach     │
│             │     │             │     │             │
│ Plan path   │     │ Generate    │     │ Guide user  │
│ Next concept│     │ 15-min      │     │ through     │
│ Adapt pace  │     │ mission     │     │ mission     │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  ┌──────────┐      ┌──────────┐       ┌──────────┐
  │ Learning │      │   RAG    │       │  Redis   │
  │ (mastery)│      │ (docs)   │       │ (memory) │
  └──────────┘      └──────────┘       └──────────┘
```

- **Strategist** — планирует путь обучения (LLM + RAG org concepts + Learning mastery), выбирает следующий концепт, адаптирует темп (remedial insertion on failure, skip on high score), кэширует пути в Redis (ai:path:{user_id}, TTL 24h)
- **Designer** — генерирует 15-минутную миссию (MissionBlueprint): RAG-grounded reading (~400w), 3 MCQ check questions, code case из реальных исходников, 2 recap-вопроса по предыдущим концептам
- **Coach** — ведёт пользователя через миссию в чат-формате, даёт подсказки

---

## Ключевая концепция: Trust Levels

| Level | Название | Описание |
|-------|----------|----------|
| 0 | Observer | Только чтение документации |
| 1 | Learner | Доступ к миссиям и квизам |
| 2 | Contributor | Может участвовать в дискуссиях |
| 3 | Practitioner | Доступ к реальным задачам из кодовой базы |
| 4 | Specialist | Может менторить других, доступ к advanced topics |
| 5 | Expert | Полный доступ, может создавать контент для организации |

Trust Level повышается автоматически на основе: выполненных миссий, mastery по концептам, streak, участия в дискуссиях.

---

## Принципы архитектуры (реализованные)

1. **Database-per-service** — у каждого сервиса своя PostgreSQL (7 БД; AI Service stateless — только Redis)
2. **Clean Architecture** — routes → services → domain ← repositories
3. **JWT shared secret** — все сервисы валидируют JWT самостоятельно, без обращения к Identity
4. **Клиент-оркестратор** — Frontend оркестрирует вызовы между сервисами
5. **Роли в JWT claims** — `role`, `is_verified`, `email_verified`, `organization_id` в extra_claims
6. **Multi-tenancy** — организации (organizations) с membership, org context в JWT
7. **Forward-only миграции** — SQL файлы, выполняются при старте сервиса, идемпотентны
8. **Redis everywhere** — все активные сервисы подключены к Redis
9. **Health checks** — `/health/live` + `/health/ready` на всех сервисах
10. **Refresh token rotation** — JWT access (1h) + refresh (30d) с family-based reuse detection
11. **Plan-based credits** — AI Service ограничивает использование Gemini по плану подписки
12. **RAG pipeline** — документы → chunks → embeddings → pgvector → semantic search
13. **Tri-Agent System** — Strategist → Designer → Coach для адаптивного обучения
14. **Trust Levels** — прогрессивный доступ к ресурсам (0–5)

---

## Что оптимизировано (Phase 1.0–1.2)

| Оптимизация | Было | Стало |
|-------------|------|-------|
| pg_trgm GIN index на courses | search p99 = 803ms | search p99 = 35ms (23x) |
| Connection pool 5 → 5/20 (min/max) | 100% saturation | 10% saturation |
| Redis cache-aside (course, curriculum) | — | TTL 5 min, cache hit |
| FK indexes (11 новых) | full table scan на JOIN | index scan |
| Cursor pagination (keyset) | offset scan | constant time |
| Health checks (/health/live, /health/ready) | — | все сервисы |
| Rate limiting (Redis sliding window) | — | 100/min global, 10/min login, 5/min register, 30/min AI endpoints |
| CORS middleware | — | env-based origins |
| XSS sanitization (bleach) | — | course/lesson content |
| JWT refresh tokens | 1h access only | access (1h) + refresh (30d) + rotation |
| Graceful shutdown | — | timeout-graceful-shutdown 25s (prod) |

---

## Чего нет (намеренно, YAGNI)

| Чего нет | Почему | Когда появится |
|----------|--------|---------------|
| API Gateway | ~~Не нужен~~ → Rust/Axum :8080, JWT verification, Redis sliding window rate limiting, reverse proxy routing to Python services, CORS (env-based origins), structured JSON request logging (X-Request-Id), health checks, Docker multi-stage build, integrated into docker-compose dev/prod | Sprint 23 (in progress) |
| Event bus (NATS) | Нет межсервисных событий, клиент оркестрирует | По необходимости |
| CI/CD pipeline | Локальная разработка | По необходимости |
| Kubernetes | Docker Compose достаточно | По необходимости |
| Proto/gRPC контракты | HTTP REST между сервисами | По необходимости |
| Video processing | Нет видео-контента в B2B pivot | По необходимости |
| Real email sending | Stub — логирование в stdout | По необходимости |
