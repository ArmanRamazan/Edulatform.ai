# EduPlatform — Roadmap

> **Пивот:** B2B Agentic Adaptive Learning для онбординга инженеров.
> Подробности в [12-AGENTIC-PIVOT.md](./12-AGENTIC-PIVOT.md).
>
> **Миссия:** Сократить онбординг инженера с 3 месяцев до 1 месяца через AI-ментора,
> обученного на кодовой базе и архитектуре компании.

---

## Стадии развития продукта

```
Foundation ✅ → Learning Intelligence ✅ → B2B Pivot (← мы здесь) → Scale (Rust Sprints 23-25)
```

| Стадия | Клиенты | Суть | Статус |
|--------|---------|------|--------|
| Foundation | — | Базовая платформа, auth, CRUD, 7 сервисов | ✅ Done |
| Learning Intelligence | — | AI-тьютор, FSRS, knowledge graph, gamification | ✅ Done |
| **B2B Pivot** | **1-50 компаний** | **RAG, Tri-Agent, Missions, Organizations** | **🔵 In Progress** |
| **Scale** | **50+ компаний** | **Rust Performance Layer (Sprints 23-25), K8s, multi-region** | **🔴 Следующий** |

---

## Навигация по документам

| # | Документ | Описание |
|---|----------|----------|
| 01 | [Видение продукта](./01-PRODUCT-VISION.md) | B2B Agentic Adaptive Learning, Tri-Agent, метрики |
| 02 | [Архитектура](./02-ARCHITECTURE-PRINCIPLES.md) | ADR, принципы, RAG pipeline, multi-tenancy |
| 03 | [Инфраструктура](./03-INFRASTRUCTURE.md) | Scaling по фазам, LLM costs, RAG sizing |
| 04 | [Домены](./04-DOMAINS.md) | Bounded contexts, event matrix |
| 05 | [Стратегия данных](./05-DATA-STRATEGY.md) | pgvector, org-scoped isolation, sizing |
| 06 | [Безопасность](./06-SECURITY.md) | Multi-tenant isolation, code security, LLM governance |
| 07 | [Видео и медиа](./07-VIDEO-MEDIA.md) | Не приоритет для MVP |
| 08 | [Монорепа и DX](./08-MONOREPO-DX.md) | Build tools, testing strategy |
| 09 | [Observability](./09-OBSERVABILITY.md) | Prometheus, Grafana, метрики |
| 10 | [Frontend](./10-FRONTEND.md) | Next.js, UI Kit, performance |
| 11 | [AI Agent Standards](./11-AI-AGENT-STANDARDS.md) | MCP, context engineering, AI safety |
| 12 | [Agentic Pivot](./12-AGENTIC-PIVOT.md) | Детальное описание пивота |

---

## Что переиспользуем из B2C

| Компонент | Новая роль |
|-----------|------------|
| Identity (auth, JWT, roles) | + Organizations, Trust Levels |
| AI service (Gemini, cache, credits) | + Tri-Agent orchestration |
| Learning (FSRS, concepts, mastery) | + Missions, session tracking |
| Knowledge graph (concepts + prerequisites) | Company knowledge graph |
| Socratic tutor | Coach Agent |
| Quiz generation | Mission question generation |
| Flashcards (FSRS) | Spaced repetition в recap |
| Streaks | Daily session streaks |
| Notification (in-app, email, DMs) | Без изменений |
| Common lib, Docker, Prometheus, Grafana | Без изменений |

---

## B2B Pivot — Sprint Plan

### Sprint 17: RAG Foundation

> Зависимости: нет. Новый сервис `services/py/rag/` (порт 8008).

| # | Задача | Описание |
|---|--------|----------|
| 17.1 | RAG service scaffold | FastAPI, pgvector extension, базовая структура |
| 17.2 | Document ingestion pipeline | Загрузка markdown, code файлов, chunking (512 tokens) |
| 17.3 | Embedding generation | Gemini Embedding API, batch processing |
| 17.4 | Semantic search endpoint | POST /search с cosine similarity, top-k results |
| 17.5 | Entity extraction | Извлечение concepts из code/docs, связи между ними |

**Результат:** можно загрузить документацию компании и искать по ней семантически.

---

### Sprint 18: Tri-Agent System

> Зависимости: Sprint 17 (RAG для контента миссий).

| # | Задача | Описание |
|---|--------|----------|
| 18.1 | Strategist Agent | Анализ профиля, построение learning path из knowledge graph |
| 18.2 | Designer Agent | Сборка 15-мин Mission из RAG-контента (recap + reading + questions + code_case) |
| 18.3 | Coach Agent | Эволюция Socratic tutor: проведение сессии, адаптивная сложность |
| 18.4 | Agent Orchestrator | Координация агентов: Strategist → Designer → Coach → feedback loop |
| 18.5 | Agent Memory | Redis-based conversation memory, session telemetry, mastery feedback |

**Результат:** три агента работают в связке, генерируют и проводят обучающие сессии.

---

### Sprint 19: Mission Engine + Trust Levels

> Зависимости: Sprint 18 (агенты создают миссии).

| # | Задача | Описание |
|---|--------|----------|
| 19.1 | Mission model | Entity: mission type (daily/review/remedial), status, score, mastery_delta |
| 19.2 | Mission lifecycle | Создание → in_progress → completed, session tracking |
| 19.3 | Daily session flow | Автоматическая генерация daily mission на основе Strategist path |
| 19.4 | Trust Level model | Levels 0-5, unlocked_areas, progression rules |
| 19.5 | Trust Level progression | Автоматическое повышение на основе mission completion + mastery |
| 19.6 | Review integration | Spaced repetition recap questions в начале каждой миссии |

**Результат:** полный цикл: ежедневная миссия → выполнение → повышение Trust Level.

---

### Sprint 20: Company Integration

> Зависимости: Sprint 17 (RAG для ingestion).

| # | Задача | Описание |
|---|--------|----------|
| 20.1 | Organization model | CRUD organizations в Identity, membership, roles (owner/admin/member) |
| 20.2 | GitHub adapter | OAuth App, clone repos, extract code + README + ADR |
| 20.3 | KB management UI (API) | CRUD knowledge bases, source management, re-index triggers |
| 20.4 | Onboarding templates | Pre-built learning paths для типовых стеков (Python, Go, JS) |
| 20.5 | Multi-tenant data isolation | org_id на всех запросах, RLS или application-level filtering |

**Результат:** компания подключает GitHub, платформа индексирует код и строит knowledge base.

---

### Sprint 21: Frontend Redesign

> Зависимости: Sprint 18-19 (Mission API, Coach API).

| # | Задача | Описание |
|---|--------|----------|
| 21.1 | Mission Dashboard | Главная страница: текущая миссия, прогресс, Trust Level |
| 21.2 | Coach Chat UI | Полноэкранный чат с Coach Agent, code highlighting |
| 21.3 | Knowledge Graph visualization | Интерактивный граф concepts компании с mastery overlay |
| 21.4 | Trust Level UI | Прогресс-бар, unlocked areas, next level requirements |
| 21.5 | Organization Switcher | Переключение между организациями, org settings |

**Результат:** новый frontend, заточенный под B2B онбординг.

---

### Sprint 22: B2B Launch

> Зависимости: Sprint 20-21 (organizations + frontend).

| # | Задача | Описание |
|---|--------|----------|
| 22.1 | Admin Dashboard | Org-level: team progress, analytics, Trust Level distribution |
| 22.2 | Team Analytics API | Агрегированные метрики: time-to-productivity, engagement, completion |
| 22.3 | B2B Pricing | Org subscriptions (Pilot/Enterprise), seat management |
| 22.4 | Billing Page | Stripe integration для org billing, invoices |

**Результат:** платформа готова к пилоту с первыми B2B-клиентами.

---

### Sprint 23: Rust API Gateway

> Зависимости: нет (параллельно со Sprint 19-22).

| # | Задача | Описание |
|---|--------|----------|
| 23.1 | Gateway scaffold | Axum server, config, health checks |
| 23.2 | JWT middleware | Token validation, claims extraction |
| 23.3 | Rate limiting | Redis sliding window, per-route limits |
| 23.4 | Reverse proxy | Route to Python services, timeout, retry |
| 23.5 | CORS + logging | CORS middleware, structured request logging |

**Результат:** единая точка входа с auth и rate limiting.

---

### Sprint 24: Rust RAG Performance

> Зависимости: Sprint 17 (RAG service существует).

| # | Задача | Описание |
|---|--------|----------|
| 24.1 | Chunker crate scaffold | pyo3 + maturin setup, Python bindings |
| 24.2 | Chunking algorithms | Regex split, overlap, token counting |
| 24.3 | RAG integration | Replace Python chunker with Rust FFI call |
| 24.4 | Search service scaffold | Axum + tantivy, index management |
| 24.5 | Search API | Full-text search endpoints, BM25 scoring |

**Результат:** chunking 10-50x быстрее, search <50ms p99.

---

### Sprint 25: Rust IO Performance

> Зависимости: Sprint 23 (gateway pattern).

| # | Задача | Описание |
|---|--------|----------|
| 25.1 | Embedding orchestrator | Axum service, batch parallel HTTP calls |
| 25.2 | Embedding API | Endpoints for single + batch embedding |
| 25.3 | RAG integration | Replace Python embedding calls with Rust service |
| 25.4 | WebSocket gateway | tokio-tungstenite, connection management |
| 25.5 | WS integration | Coach chat + notification real-time channels |

**Результат:** embedding throughput 10-40x, real-time messaging.

---

## Dormant Services (B2C)

Следующие сервисы сохранены, но не развиваются активно:

| Сервис | Причина | Статус |
|--------|---------|--------|
| Course (8002) | B2C marketplace не нужен для B2B | Dormant |
| Enrollment (8003) | Заменён org membership + missions | Dormant |
| Payment (8004) | Индивидуальные платежи → org subscriptions | Dormant (кроме org billing) |

---

## Принцип принятия решений

```
B2B first: каждая фича решает проблему онбординга инженеров.
AI-native: агенты — ядро продукта, не надстройка.
Pilot → Enterprise: начинаем с 1-5 компаний, доказываем ROI.
Переиспользуем максимум: 70%+ инфраструктуры из B2C фазы.
```

---

## Sprint Execution Summary

| Sprint | Название | Задач | Зависимости | Статус |
|--------|----------|-------|-------------|--------|
| 17 | RAG Foundation | 5 | — | 🔴 |
| 18 | Tri-Agent System | 5 | 17 | 🔴 |
| 19 | Mission Engine + Trust Levels | 6 | 18 | 🔴 |
| 20 | Company Integration | 5 | 17 | 🔴 |
| 21 | Frontend Redesign | 5 | 18, 19 | 🔴 |
| 22 | B2B Launch | 4 | 20, 21 | 🔴 |
| **23** | **Rust API Gateway** | **5** | **— (параллельно)** | **🔴** |
| **24** | **Rust RAG Performance** | **5** | **17** | **🔴** |
| **25** | **Rust IO Performance** | **5** | **23** | **🔴** |

**Total: 45 задач, 9 спринтов (6 B2B MVP + 3 Rust Scale).**
