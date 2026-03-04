# Phase 3 — B2B Agentic Adaptive Learning [ACTIVE]

> **Пивот:** продукт перешел от B2C course marketplace к B2B AI-powered engineering onboarding.
>
> **Цель:** построить Tri-Agent систему с RAG, Mission Engine и организационной моделью для онбординга инженеров.
>
> **Статус:** 🟡 В разработке (Sprints 17-22)

---

## Бизнес-модель

B2B SaaS для технологических компаний. Продукт автоматизирует онбординг новых инженеров через:

1. **RAG** — индексация кодовой базы, документации, внутренних wiki компании
2. **Tri-Agent System** — Strategist (план), Designer (контент), Coach (обучение)
3. **15-min Daily Missions** — микрообучение, адаптированное под уровень инженера
4. **Trust Levels (0-5)** — прогрессия от базовых понятий до production-ready contributions

---

## Sprint 17 — RAG Foundation

> Сервис для индексации и семантического поиска по кодовой базе и документации компании.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| 17.1 | Scaffold RAG Service (FastAPI, Clean Architecture, :8008) | backend:rag | 🔴 |
| 17.2 | Embedding client: OpenAI / local model adapter | backend:rag | 🔴 |
| 17.3 | Document ingestion pipeline: upload → chunk → embed → store (pgvector) | backend:rag | 🔴 |
| 17.4 | Semantic search: POST /rag/search {query, org_id} → ranked chunks | backend:rag | 🔴 |
| 17.5 | Entity extraction: extract functions, classes, concepts from code | backend:rag | 🔴 |

**Новая БД:** rag-db (:5439) с pgvector extension

---

## Sprint 18 — Tri-Agent System

> Три специализированных AI-агента, работающих последовательно: Strategist → Designer → Coach.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| 18.1 | **Strategist Agent** — анализ кодовой базы, определение learning path, выбор тем | backend:ai | 🔴 |
| 18.2 | **Designer Agent** — генерация mission-контента на основе реального кода компании | backend:ai | 🔴 |
| 18.3 | **Coach Agent** — Socratic dialog, подсказки, review ответов (расширение Tutor) | backend:ai | 🔴 |
| 18.4 | **Agent Orchestrator** — pipeline Strategist → Designer → Coach, state management | backend:ai | 🔴 |
| 18.5 | **Agent Memory** — персистентная память агентов (Redis + PostgreSQL) | backend:ai | 🔴 |

**Архитектура:**
```
Strategist (план обучения)
    → Designer (генерация миссий из кода компании)
        → Coach (сопровождение инженера в реальном времени)
```

---

## Sprint 19 — Mission Engine + Trust Levels

> Движок ежедневных 15-минутных миссий с системой уровней доверия.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| 19.1 | Mission model: missions, mission_steps, mission_attempts | backend:learning | 🔴 |
| 19.2 | Mission Service: create, assign, submit, evaluate | backend:learning | 🔴 |
| 19.3 | Trust Level system (0-5): progression rules, thresholds, history | backend:learning | 🔴 |
| 19.4 | Daily Session API: GET /sessions/today → today's mission set | backend:learning | 🔴 |
| 19.5 | Mission-review integration: Coach Agent reviews mission submissions | backend:ai | 🔴 |
| 19.6 | Mission types: code_reading, code_writing, architecture_quiz, PR_review | backend:learning | 🔴 |

**Trust Levels:**

| Level | Название | Описание |
|-------|----------|----------|
| 0 | Observer | Чтение документации, обзор архитектуры |
| 1 | Reader | Чтение и понимание кода, ответы на вопросы |
| 2 | Contributor | Небольшие изменения, fix typos, write tests |
| 3 | Developer | Самостоятельные задачи, feature development |
| 4 | Reviewer | Code review, архитектурные решения |
| 5 | Expert | Менторство, system design, production ownership |

---

## Sprint 20 — Company Integration

> Multi-tenancy: организации, GitHub adapter, knowledge base management.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| 20.1 | Organization model: orgs, org_members, org_settings + migration | backend:identity | 🔴 |
| 20.2 | GitHub adapter: clone repo, extract structure, track changes | backend:rag | 🔴 |
| 20.3 | Knowledge Base management: CRUD endpoints для org KB | backend:rag | 🔴 |
| 20.4 | Markdown ingestion: internal docs, wiki, runbooks → chunks | backend:rag | 🔴 |
| 20.5 | Onboarding templates: pre-built mission sets per tech stack | backend:learning | 🔴 |

**DB Schema (identity-db — расширение):**
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    settings JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE org_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'member',  -- owner, admin, member
    joined_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(org_id, user_id)
);
```

---

## Sprint 21 — Frontend Redesign

> Новый UI для B2B: mission dashboard, Coach chat, knowledge graph, trust levels.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| 21.1 | Mission Dashboard: today's missions, progress, timer | frontend:buyer | 🔴 |
| 21.2 | Coach Chat UI: real-time Socratic dialog с контекстом кода | frontend:buyer | 🔴 |
| 21.3 | Knowledge Graph visualization: tech stack map, mastery overlay | frontend:buyer | 🔴 |
| 21.4 | Trust Level UI: progression bar, level badge, history | frontend:buyer | 🔴 |
| 21.5 | Org Switcher: переключение между организациями, org settings | frontend:buyer | 🔴 |

---

## Sprint 22 — B2B Launch

> Admin tools, аналитика, тарификация для компаний.

| # | Задача | Scope | Статус |
|---|--------|-------|--------|
| 22.1 | Admin Dashboard: team overview, progress tracking, bottleneck detection | frontend:buyer | 🔴 |
| 22.2 | Team Analytics: onboarding velocity, trust level distribution, mission completion rates | backend:learning | 🔴 |
| 22.3 | B2B pricing model: per-seat, tiers (starter/growth/enterprise) | backend:payment | 🔴 |
| 22.4 | Billing page: plan management, invoices, seat management | frontend:buyer | 🔴 |

---

## Критерии завершения Phase 3

- [ ] RAG Service индексирует GitHub repo и возвращает релевантные chunks
- [ ] Tri-Agent pipeline генерирует персонализированные missions из кода компании
- [ ] Trust Level 0→5 progression работает с автоматическим повышением
- [ ] 15-min daily session flow полностью функционален
- [ ] Organization multi-tenancy: создание org, invite members, org-scoped данные
- [ ] Admin dashboard с team analytics
- [ ] B2B pricing и billing
- [ ] Можно провести pilot с реальной командой (5-10 инженеров)
