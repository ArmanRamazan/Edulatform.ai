# Monorepo Structure

> Принципы: **YAGNI** — только то, что нужно сейчас. **SRP** — один сервис = один домен. **DIP** — сервисы зависят от контрактов (proto), не друг от друга.

---

## Дерево

```
eduplatform/
│
├── proto/                         # Контракты между сервисами (source of truth)
│   ├── identity/v1/               #   Auth, users, roles
│   ├── course/v1/                 #   Courses, lessons, materials
│   ├── enrollment/v1/             #   Enrollment, progress
│   └── events/v1/                 #   Domain events (async)
│
├── libs/                          # Shared код (минимум, только DRY)
│   ├── py/
│   │   ├── common/                #   Config, errors, security, database, health, logging, rate_limit, sentry
│   │   └── db/                    #   DB connection, migration helpers
│   └── rs/
│       ├── common/src/            #   Error types, config, tracing setup
│       ├── proto-gen/src/         #   Сгенерированный код из proto/
│       └── rag-chunker/           #   pyo3 chunker: text/code/markdown splitting + metadata for RAG (maturin build)
│
├── services/                      # Deployable сервисы
│   ├── py/                        # Python сервисы (бизнес-логика)
│   │   ├── identity/              #   Auth, JWT refresh tokens, roles, admin, email verification, forgot password
│   │   ├── course/                #   CRUD курсов, поиск, модули, уроки, отзывы, категории, фильтрация, XSS sanitization, bundles, wishlist
│   │   ├── enrollment/            #   Запись на курс, прогресс, lesson completion, auto-completion, recommendations
│   │   ├── payment/               #   Mock-оплата, Stripe SDK adapter, подписки, teacher earnings, payouts, coupons, invoice PDF, refunds, org subscriptions (seat-based B2B)
│   │   ├── notification/          #   In-app уведомления, email (lifecycle events), direct messaging
│   │   ├── ai/                    #   Quiz generation, summary generation (Gemini Flash), Redis cache, configurable LLM provider per org (Gemini/self-hosted)
│   │   ├── learning/              #   Quiz persistence, flashcards (FSRS), knowledge graph, streaks, leaderboard, XP, badges, discussions, activity feed, certificates, missions, trust levels
│   │   ├── rag/                   #   Document ingestion, pgvector semantic search, LLM concept extraction, knowledge base, GitHub adapter
│   │   └── mcp/                   #   MCP server for AI tool integration (Cursor, Claude Desktop), 17 tools + 4 resources
│   └── rs/                        # Rust сервисы (performance-critical)
│       ├── api-gateway/           #   Axum :8080, JWT auth, rate limiting, reverse proxy, CORS, Dockerfile (multi-stage)
│       ├── search/                #   Axum :8010, tantivy full-text search, BM25 scoring, org-scoped indexing
│       ├── embedding-orchestrator/#   Axum :8009, parallel embedding API calls, semaphore-based concurrency, batch processing
│       ├── ws-gateway/            #   Axum :8011, WebSocket gateway for real-time messaging (Coach chat, notifications)
│       ├── video-processor/       #   Upload, transcode, stream
│       └── payment-engine/        #   Транзакции, подписки, payouts
│
├── apps/                          # Frontend приложения (Next.js)
│   ├── buyer/                     #   B2B knowledge app (SSR/SSG/Client)
│   │   ├── app/(marketing)/       #     Public: landing, login, register (no sidebar)
│   │   ├── app/(app)/             #     Authenticated: dashboard, courses, flashcards, org (sidebar)
│   │   ├── components/ui/         #     shadcn/ui components (Dark Knowledge theme)
│   │   ├── components/layout/     #     Sidebar, TopBar, CommandPalette
│   │   ├── components/dashboard/  #     Dashboard grid + 7 endpoint-driven blocks
│   │   ├── components/graph/     #     Concept Hub: ConceptHeader, InternalSources, Missions, TeamMastery, Discussions, RelatedGraph
│   │   └── components/search/    #     Smart Search: SearchView, Internal/External results, RouteIndicator
│   └── seller/                    #   Дашборд преподавателя (Client-side)
│
├── packages/                      # Shared frontend пакеты
│   ├── ui/                        #   UI Kit: Radix + Tailwind компоненты
│   ├── api-client/                #   Typed API client (codegen из OpenAPI)
│   └── shared/                    #   Validators, formatters, constants
│
├── deploy/                        # Infrastructure
│   ├── docker/                    #   Dockerfiles per service
│   ├── scripts/                   #   Ops scripts (backup, restore, list-backups)
│   ├── staging/                   #   Staging env config (.env.staging.example)
│   └── k8s/base/                  #   K8s manifests
│
├── tools/                         # Dev utilities
│   ├── seed/                      #   Database seeding scripts
│   ├── locust/                    #   Load test scenarios
│   └── orchestrator/              #   AI orchestrator: autonomous Claude Code executor
│       ├── orchestrator.py        #     YAML task parser, task executor, state persistence
│       ├── run.sh                 #     Launcher script (./run.sh tasks/sprint-21.yaml)
│       ├── run-b2b.sh             #     B2B build pipeline (4-phase parallel execution)
│       ├── tasks/                 #     Sprint YAML files (sprint-21 through sprint-27, done/, on_hold/)
│       └── pyproject.toml         #     uv workspace member (pure stdlib, no deps)
│
└── docs/                          # Документация (goals, phases, ADR)
```

---

## Почему именно так

### Что есть и почему

| Решение | Принцип | Обоснование |
|---------|---------|-------------|
| `proto/` на верхнем уровне | **DIP** | Контракты — это абстракции. Сервисы зависят от них, не друг от друга |
| `services/py/` и `services/rs/` | **SRP** | Четкое разделение по языку и runtime. Разные build pipelines |
| `libs/` минимальный | **YAGNI** | Только config, logging, db utils. Абстракции появятся когда будет 2+ потребителя |
| Каждый Python сервис: `routes → services → domain → repositories` | **SRP + DIP** | Clean Architecture слои. Domain не знает про HTTP и БД |
| `events/v1/` в proto | **OCP** | Новые события добавляются без изменения существующих сервисов |
| `deploy/` отдельно от сервисов | **SRP** | Инфраструктура не смешивается с бизнес-логикой |
| `apps/` для фронтенда, `packages/` для shared | **SRP** | Студент и преподаватель — разные приложения с разными требованиями к рендерингу и аудиториями |
| `packages/ui/` отдельно | **DRY + OCP** | Единый UI Kit для всех приложений. Новый app использует готовые компоненты |
| `packages/api-client/` с codegen | **DIP** | Фронтенд зависит от сгенерированного контракта, не от деталей реализации API |

### Чего НЕТ и почему (YAGNI)

| Чего нет | Когда появится | Триггер для создания |
|----------|---------------|---------------------|
| `services/py/moderation/` | Phase 2 | Когда будет > 1000 курсов и нужна модерация контента |
| `services/py/analytics-api/` | Phase 2 | Когда teacher dashboard потребует аналитику |
| `services/rs/feed-builder/` | Phase 2 | Когда рекомендации станут приоритетом |
| `workers/` директория | Когда вырастет | Пока background jobs живут внутри сервисов. Выделим когда нужна независимая масштабируемость |
| `libs/py/testing/` | Когда будет boilerplate | Пока fixtures живут в `tests/` каждого сервиса. Выделим когда увидим дублирование |
| `terraform/` | Phase 2 | Пока Docker Compose хватает. IaC когда будет multi-env |
| ~~`apps/seller/`~~ | ~~Phase 1.7~~ | ✅ Dashboard, course CRUD, AI outline/lesson generation |

---

## Внутренняя структура Python сервиса

```
services/py/{service}/
├── app/
│   ├── routes/          # HTTP handlers (presentation layer)
│   │   └──              #   Принимает request → вызывает service → возвращает response
│   │                    #   Здесь: валидация input, HTTP коды, сериализация
│   │
│   ├── services/        # Use cases (application layer)
│   │   └──              #   Оркестрация бизнес-логики
│   │                    #   Вызывает domain + repositories + external services
│   │                    #   Транзакции и координация
│   │
│   ├── domain/          # Бизнес-правила (domain layer)
│   │   └──              #   Entities, Value Objects, Domain Events
│   │                    #   НЕ зависит от фреймворков, БД, HTTP
│   │                    #   Чистый Python, максимум dataclasses
│   │
│   ├── repositories/    # Доступ к данным (infrastructure layer)
│   │   └──              #   Абстрактный интерфейс + SQL реализация
│   │                    #   Маппинг domain entities ↔ DB rows
│   │
│   └── adapters/        # Внешние сервисы (infrastructure layer, optional)
│       └──              #   HTTP клиенты к другим сервисам (fire-and-forget)
│                        #   Пример: WsPublisher для WebSocket gateway
│
├── tests/               # Тесты рядом с кодом
│   └──                  #   Unit: мокают repositories
│                        #   Integration: реальная БД (testcontainers)
│
└── migrations/          # SQL миграции (alembic или raw SQL)
```

**Правило зависимостей** (Dependency Rule):
```
routes → services → domain ← repositories
                      ↑
              Ничто не зависит от routes
              Domain не зависит ни от чего внешнего
```

---

## Внутренняя структура Rust сервиса

```
services/rs/{service}/
├── src/
│   ├── main.rs          # Точка входа, wiring
│   ├── config.rs        # Конфигурация из env
│   ├── routes/          # HTTP/gRPC handlers
│   ├── services/        # Бизнес-логика
│   └── adapters/        # Внешние зависимости (DB, Redis, S3)
├── tests/               # Integration tests
├── Cargo.toml
└── Dockerfile
```

---

## Внутренняя структура Frontend приложения

```
apps/{app}/
├── app/                         # Next.js App Router
│   ├── (marketing)/             #   Public pages (landing, auth) — no sidebar
│   │   ├── login/
│   │   ├── register/
│   │   └── page.tsx             #     Landing page
│   ├── (app)/                   #   Authenticated app — sidebar + TopBar layout
│   │   ├── layout.tsx           #     Sidebar + TopBar wrapper
│   │   ├── dashboard/           #     Endpoint-driven dashboard blocks
│   │   ├── courses/             #     Course pages (catalog, detail, lesson)
│   │   ├── flashcards/
│   │   ├── badges/
│   │   ├── org/                 #     Organization selector
│   │   ├── settings/analytics/  #     Team analytics (admin: overview, heatmap, bottlenecks)
│   │   ├── settings/billing/    #     Org subscription billing (Stripe integration)
│   │   └── ...
│   ├── layout.tsx               #   Root layout (fonts, providers)
│   └── globals.css              #   Dark Knowledge theme CSS variables
├── components/                  #   Компоненты специфичные для этого app
│   ├── ui/                      #     shadcn/ui components (16: button, card, badge, input, dialog, alert-dialog, etc.)
│   ├── layout/                  #     Sidebar.tsx, TopBar.tsx, CommandPalette.tsx
│   ├── dashboard/               #     DashboardGrid.tsx, BlockErrorBoundary.tsx
│   │   └── blocks/              #     7 dashboard blocks (Greeting, Mission, TrustLevel, etc.)
│   ├── search/                  #     SearchView.tsx, InternalResultsSection, ExternalResultsSection, RouteIndicator
│   ├── mission/                 #     MissionSession.tsx, MissionComplete.tsx, PhaseIndicator.tsx (5-phase Socratic session)
│   ├── admin/analytics/         #     TeamOverview, ConceptCoverage (heatmap), BottleneckReport
│   ├── admin/billing/           #     BillingPage.tsx, PaymentForm.tsx (Stripe Elements)
│   └── providers/               #     OrgProvider.tsx, Providers.tsx (QueryClient)
├── hooks/                       #   Custom React hooks (TanStack Query)
│   ├── use-auth.ts              #     Login/register/logout (не server state)
│   ├── use-active-org.ts        #     Active organization from context
│   ├── use-organizations.ts     #     Organization API hooks
│   ├── use-search.ts            #     useInternalSearch, useExternalSearch, classifyQuery (AI router)
│   ├── use-courses.ts           #     useCourseList, useCourse, useCurriculum, useCategories
│   ├── use-enrollments.ts       #     useMyEnrollments, useEnroll (mutation)
│   ├── use-concepts.ts          #     useCourseGraph, useCourseMastery, useCreateConcept, useDeleteConcept
│   ├── use-flashcards.ts        #     useDueCards, useDueCount, useReviewCard, useCreateFlashcard
│   ├── use-gamification.ts      #     useMyXp, useMyXpHistory, useMyBadges, useMyStreak
│   ├── use-coach.ts             #     useStartCoachSession, useSendCoachMessage, useEndCoachSession
│   ├── use-analytics.ts         #     useTeamOverview, useConceptCoverage, useBottlenecks (org admin analytics)
│   ├── use-billing.ts           #     useOrgSubscription, useCreateOrgSubscription, useCancelOrgSubscription
│   └── ...
├── lib/                         #   API вызовы, утилиты, конфиг
│   └── api.ts                   #     Typed API namespaces
├── public/                      #   Статика (favicon, robots.txt)
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

**Правила:**
- `app/` — только page.tsx, layout.tsx, loading.tsx, error.tsx. Без бизнес-логики
- Route groups: `(marketing)` для публичных страниц (no sidebar), `(app)` для authenticated + sidebar
- `components/ui/` — shadcn/ui компоненты (Dark Knowledge theme)
- `components/` — UI специфичный для приложения. Общее — в `packages/ui/`
- Dashboard blocks pattern: каждый блок = один API вызов, независимый error boundary (`BlockErrorBoundary`)
- `hooks/` — data fetching, form logic, local state. Не дублировать между apps — выносить в `packages/shared/`
- `lib/` — обертки над `packages/api-client/`, конфиг, auth helpers
- Server Components по умолчанию. `"use client"` только когда нужен interactivity

## Shared UI Kit (`packages/ui/`)

```
packages/ui/
├── components/
│   ├── button.tsx         # Каждый компонент — один файл
│   ├── input.tsx          # Экспорт через index.ts
│   ├── modal.tsx
│   ├── video-player.tsx
│   └── ...
├── tokens/
│   ├── colors.ts          # Design tokens как JS объекты
│   ├── spacing.ts
│   └── typography.ts
├── index.ts               # Public API пакета
├── tailwind.config.ts     # Shared Tailwind preset
├── tsconfig.json
└── package.json
```

**Правила:**
- Каждый компонент — самодостаточный, без внешних зависимостей кроме Radix и Tailwind
- Props типизированы, дефолты указаны, forwardRef где нужен DOM доступ
- Не содержит бизнес-логику. Только UI: рендер, стили, accessibility, анимации

---

## Принципы расширения

1. **Новый сервис** — создай директорию в `services/py/` или `services/rs/`, добавь proto контракт
2. **Новый event** — определи в `proto/events/v1/`, сгенерируй код, подпишись в нужном сервисе
3. **Shared код** — сначала скопируй. Если дублируется в 3+ местах — вынеси в `libs/`
4. **Новый worker** — пока живет внутри сервиса. Выделяй когда нужна независимая масштабируемость
5. **Новый frontend app** — создай директорию в `apps/`, переиспользуй `packages/ui/` и `packages/api-client/`
6. **Новый UI компонент** — если используется в 1 app → в `apps/{app}/components/`. Если в 2+ → в `packages/ui/`
