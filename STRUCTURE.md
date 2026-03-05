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
│       └── proto-gen/src/         #   Сгенерированный код из proto/
│
├── services/                      # Deployable сервисы
│   ├── py/                        # Python сервисы (бизнес-логика)
│   │   ├── identity/              #   Auth, JWT refresh tokens, roles, admin, email verification, forgot password
│   │   ├── course/                #   CRUD курсов, поиск, модули, уроки, отзывы, категории, фильтрация, XSS sanitization, bundles, wishlist
│   │   ├── enrollment/            #   Запись на курс, прогресс, lesson completion, auto-completion, recommendations
│   │   ├── payment/               #   Mock-оплата, Stripe SDK adapter, подписки, teacher earnings, payouts, coupons, invoice PDF, refunds
│   │   ├── notification/          #   In-app уведомления, email (lifecycle events), direct messaging
│   │   ├── ai/                    #   Quiz generation, summary generation (Gemini Flash), Redis cache
│   │   ├── learning/              #   Quiz persistence, flashcards (FSRS), knowledge graph, streaks, leaderboard, XP, badges, discussions, activity feed, certificates, missions, trust levels
│   │   └── rag/                   #   Document ingestion, pgvector semantic search, LLM concept extraction, knowledge base
│   └── rs/                        # Rust сервисы (performance-critical)
│       ├── api-gateway/           #   Routing, auth check, rate limiting
│       ├── search/                #   Поисковый proxy + ranking
│       ├── video-processor/       #   Upload, transcode, stream
│       └── payment-engine/        #   Транзакции, подписки, payouts
│
├── apps/                          # Frontend приложения (Next.js)
│   ├── buyer/                     #   Студенческий сайт (SSR/SSG/Client)
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
│       ├── run.sh                 #     Launcher script (./run.sh tasks/sprint-1.yaml)
│       ├── tasks/                 #     Sprint YAML files (sprint-1 through sprint-4, phase-2.0 through phase-3.5)
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
│   └── repositories/    # Доступ к данным (infrastructure layer)
│       └──              #   Абстрактный интерфейс + SQL реализация
│                        #   Маппинг domain entities ↔ DB rows
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
├── app/                   # Next.js App Router
│   ├── (group)/           #   Route groups (без влияния на URL)
│   │   ├── page.tsx       #     Server Component по умолчанию
│   │   ├── layout.tsx     #     Layout для группы
│   │   ├── loading.tsx    #     Streaming skeleton
│   │   └── error.tsx      #     Error boundary
│   ├── layout.tsx         #   Root layout
│   └── globals.css        #   Tailwind directives
├── components/            #   Компоненты специфичные для этого app
│   ├── Header.tsx         #     Навигация, auth state, email verification banner
│   ├── Providers.tsx      #     QueryClientProvider (TanStack Query)
│   ├── CourseCardSkeleton.tsx  #  Loading skeleton для курсов
│   ├── TutorDrawer.tsx    #     Slide-out chat panel для AI-тьютора на уроке
│   └── ...                #     Используют packages/ui как основу
├── hooks/                 #   Custom React hooks (TanStack Query)
│   ├── use-auth.ts        #     Login/register/logout (не server state)
│   ├── use-courses.ts     #     useCourseList, useCourse, useCurriculum, useCategories
│   ├── use-enrollments.ts #     useMyEnrollments, useEnroll (mutation)
│   ├── use-reviews.ts     #     useCourseReviews, useCreateReview (optimistic)
│   ├── use-progress.ts    #     useCourseProgress, useCompleteLesson (optimistic)
│   ├── use-notifications.ts #   useMyNotifications, useMarkRead (optimistic)
│   ├── use-quiz.ts        #     useQuiz, useSubmitQuiz, useMyAttempts
│   ├── use-ai.ts          #     useGenerateQuiz, useSummary
│   ├── use-tutor.ts       #     useTutorChat, useTutorFeedback
│   ├── use-concepts.ts    #     useCourseGraph, useCourseMastery, useCreateConcept, useDeleteConcept
│   ├── use-flashcards.ts  #     useDueCards, useDueCount, useReviewCard, useCreateFlashcard
│   └── use-gamification.ts #    useMyXp, useMyXpHistory, useMyBadges, useMyStreak
├── lib/                   #   API вызовы, утилиты, конфиг
├── public/                #   Статика (favicon, robots.txt)
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

**Правила:**
- `app/` — только page.tsx, layout.tsx, loading.tsx, error.tsx. Без бизнес-логики
- `components/` — UI специфичный для приложения. Общее — в `packages/ui/`
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
