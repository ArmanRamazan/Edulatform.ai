# 04 — Домены и Bounded Contexts

> Владелец: Architect / Principal Developer
> Последнее обновление: 2026-03-05
>
> Обновлено под B2B Agentic Adaptive Learning pivot.

---

## Domain Map

```
┌─────────────────────────────────────────────────────────────────┐
│                     EDUPLATFORM (B2B)                            │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Identity &   │  │  Knowledge   │  │     AI Agents        │  │
│  │  Access       │  │  Management  │  │  (Strategist,        │  │
│  │  + Orgs       │  │  (RAG)       │  │   Designer, Coach)   │  │
│  │  ✅ + 🔴      │  │  🔴 Sprint 17│  │  🔴 Sprint 18       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Learning     │  │Notifications │  │     Billing          │  │
│  │  Engine       │  │              │  │  (Org Subscriptions) │  │
│  │  + Missions   │  │  ✅          │  │  🔴 Sprint 22       │  │
│  │  + Trust Lvls │  │              │  │                      │  │
│  │  ✅ + 🔴      │  │              │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  DORMANT (B2C)                                           │   │
│  │  Course │ Enrollment │ Individual Payments                │   │
│  │  💤       💤            💤                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

✅ = реализовано   🔴 = в разработке   💤 = dormant
```

---

## Домен 1: Identity & Access ✅ + Organizations 🔴

**Бизнес-цель:** Аутентификация, авторизация, управление организациями и membership.

**Сервис:** Identity (:8001)

### Существующее (✅)

| # | Возможность | Статус |
|---|-------------|--------|
| 1.1 | User model (student, teacher, admin) | ✅ |
| 1.2 | JWT auth (access + refresh tokens, role в claims) | ✅ |
| 1.3 | Register, Login, GET /me, PATCH /me | ✅ |
| 1.4 | Admin: verify teachers, list users | ✅ |
| 1.5 | Email verification, forgot password | ✅ |
| 1.6 | Rate limiting, CORS, XSS sanitization | ✅ |
| 1.7 | Public profiles, follows | ✅ |
| 1.8 | Referral program | ✅ |

### Новое для B2B (🔴 Sprint 20)

| # | Возможность | Описание |
|---|-------------|----------|
| 1.9 | Organization model | CRUD orgs, settings, branding |
| 1.10 | Org Membership | Roles: owner, admin, member. Invite flow |
| 1.11 | Org-scoped JWT | org_id в JWT claims, middleware для org context |
| 1.12 | Trust Level storage | Per-user per-org trust level (0-5) |

**Владение данными:** users, refresh_tokens, organizations, org_memberships, trust_levels

---

## Домен 2: Knowledge Management (RAG) 🔴

**Бизнес-цель:** Загрузка, индексация и семантический поиск по кодовой базе и документации компании.

**Сервис:** RAG (:8008) — **новый, Sprint 17**

| # | Возможность | Sprint | Описание |
|---|-------------|--------|----------|
| 2.1 | Document ingestion | 17 | Upload markdown, code files, chunking (512 tokens) |
| 2.2 | Embedding generation | 17 | Gemini Embedding API, batch processing |
| 2.3 | Semantic search | 17 | POST /search, cosine similarity, top-k results |
| 2.4 | Entity extraction | 17 | Concepts из code/docs, relationships |
| 2.5 | GitHub adapter | 20 | OAuth, clone repos, extract code + README + ADR |
| 2.6 | KB management API | 20 | CRUD knowledge bases, re-index triggers |

**Владение данными:** documents, chunks, embeddings (pgvector), extracted_concepts, knowledge_bases

---

## Домен 3: AI Agents 🔴

**Бизнес-цель:** Tri-Agent system для адаптивного обучения. Ядро продукта.

**Сервис:** AI (:8006) — расширение существующего

### Существующее (✅)

| # | Возможность | Статус |
|---|-------------|--------|
| 3.1 | Gemini Flash integration | ✅ |
| 3.2 | Redis кэш + conversation memory | ✅ |
| 3.3 | Plan-based credits | ✅ |
| 3.4 | Socratic tutor pipeline | ✅ |
| 3.5 | Quiz/summary generation | ✅ |

### Новое для B2B (🔴 Sprint 18)

| # | Возможность | Описание |
|---|-------------|----------|
| 3.6 | Strategist Agent | Learning path из mastery graph + company KB |
| 3.7 | Designer Agent | Mission assembly из RAG content |
| 3.8 | Coach Agent | Эволюция Socratic tutor, session-based dialogue |
| 3.9 | Agent Orchestrator | Strategist → Designer → Coach → feedback loop |
| 3.10 | Agent Memory | Redis session state, telemetry, mastery feedback |

**Владение данными:** prompt templates, AI cache, agent memory (Redis), conversation history

---

## Домен 4: Learning Engine ✅ + Missions 🔴

**Бизнес-цель:** Adaptive learning: missions, trust levels, spaced repetition, mastery tracking.

**Сервис:** Learning (:8007) — расширение существующего

### Существующее (✅)

| # | Возможность | Статус |
|---|-------------|--------|
| 4.1 | Quizzes (CRUD, submit, scoring) | ✅ |
| 4.2 | FSRS flashcards (scheduling, review) | ✅ |
| 4.3 | Concepts + prerequisites (knowledge graph) | ✅ |
| 4.4 | Concept mastery tracking (0.0 → 1.0) | ✅ |
| 4.5 | XP, streaks, badges, leaderboard | ✅ |
| 4.6 | Discussions (threaded, pinning) | ✅ |

### Новое для B2B (🔴 Sprint 19)

| # | Возможность | Описание |
|---|-------------|----------|
| 4.7 | Mission model | Entity: type, status, score, mastery_delta, content blocks |
| 4.8 | Mission lifecycle | pending → in_progress → completed, session tracking |
| 4.9 | Daily session flow | Auto-generation via Strategist, scheduling |
| 4.10 | Trust Level progression | Auto-upgrade based on mastery + mission completion |
| 4.11 | Review integration | FSRS recap questions в начале каждой Mission |
| 4.12 | Org-scoped leaderboard | Leaderboard внутри организации |

**Владение данными:** missions, trust_level_history, quizzes, flashcards, concepts, concept_mastery, streaks, badges, xp

---

## Домен 5: Notifications ✅

**Бизнес-цель:** Уведомления и messaging. Без изменений для B2B.

**Сервис:** Notification (:8005)

| # | Возможность | Статус |
|---|-------------|--------|
| 5.1 | In-app notifications (POST, GET /me, PATCH /read) | ✅ |
| 5.2 | FSRS review reminders | ✅ |
| 5.3 | Streak at risk reminders | ✅ |
| 5.4 | Direct messaging | ✅ |
| 5.5 | Email delivery (SMTP) | 🔴 Future |

**Владение данными:** notifications, conversations, messages

---

## Домен 6: Billing 🔴

**Бизнес-цель:** Org subscriptions, seat management, invoicing.

**Сервис:** Payment (:8004) — переориентация с individual payments

| # | Возможность | Sprint | Описание |
|---|-------------|--------|----------|
| 6.1 | Org subscription model | 22 | Pilot/Enterprise tiers, monthly billing |
| 6.2 | Seat management | 22 | Add/remove seats, pro-rating |
| 6.3 | Stripe org billing | 22 | Stripe Checkout для org payments |
| 6.4 | Invoices | 22 | Auto-generated monthly invoices |

**Владение данными:** org_subscriptions, org_invoices, seat_allocations

### Dormant (B2C)
Существующие таблицы (payments, subscriptions, earnings, coupons, gifts) остаются, но не развиваются.

---

## DORMANT Domains (B2C)

Сохранены в кодовой базе, но не развиваются активно.

| Домен | Сервис | Причина dormancy |
|-------|--------|-----------------|
| Course & Content | Course (:8002) | B2C marketplace не нужен для B2B onboarding |
| Enrollment | Enrollment (:8003) | Заменён org membership + missions |
| Individual Payments | Payment (:8004) | Заменён org subscriptions |
| Reviews & Ratings | Course (:8002) | Часть B2C marketplace |
| Search & Discovery | Course (:8002) | Каталог курсов не нужен |

---

## Матрица событий между доменами

| Событие | Источник | Подписчики |
|---------|----------|-----------|
| `user.registered` | Identity | Notifications |
| `org.member_added` | Identity | Learning Engine (init trust level), Notifications |
| `document.ingested` | RAG | AI Agents (invalidate cached paths) |
| `kb.reindexed` | RAG | AI Agents (refresh concept graph) |
| `mission.generated` | AI Agents | Learning Engine (persist mission) |
| `mission.completed` | Learning Engine | AI Agents (telemetry → Strategist), Notifications |
| `trust_level.upgraded` | Learning Engine | Identity (update claims), Notifications |
| `concept.mastered` | Learning Engine | AI Agents (update Strategist path) |
| `streak.at_risk` | Learning Engine | Notifications |
| `org.subscription_created` | Billing | Identity (activate org) |

> **Текущая реализация:** прямые HTTP вызовы между сервисами. Event bus (NATS) — Phase Scale.
