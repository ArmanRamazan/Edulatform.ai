# 02 — Архитектурные принципы и ADR

> Владелец: Architect
> Последнее обновление: 2026-03-05
>
> Обновлено под B2B Agentic Adaptive Learning pivot.

---

## Принципы архитектуры

### P1. Python для бизнес-логики, Rust для performance-critical paths

- **Python** — API, бизнес-логика, AI agent orchestration, RAG pipeline, Learning Engine
- **Rust** — API Gateway, Search (tantivy), Embedding Orchestrator, WebSocket Gateway, RAG Chunker (pyo3 FFI). Sprints 23-25
- **Решение о языке:** p99 < 50ms или > 10K RPS → Rust. Остальное → Python

### P2. Монорепа с четкими границами

- Единый репозиторий, строгие boundaries между доменами
- Shared протоколы через protobuf (Phase Scale)
- Независимый деплой каждого сервиса
- Каждый сервис — своя БД, никогда не читает чужую

### P3. Multi-tenant by default

- Каждый запрос к данным — с `org_id` в WHERE clause
- Application-level isolation (не database-level): одна БД, org_id фильтрация
- Все новые таблицы содержат `organization_id` (кроме общесистемных: users, auth)
- API endpoints принимают org context из JWT или path parameter

### P4. Design for 10x, build for 1x

- Архитектура выдерживает 10x от текущей нагрузки без переписывания
- Реализуем только то, что нужно сейчас
- Каждое решение заменяемо за 2 недели

### P5. Observable by default

- Каждый сервис — метрики, логи, трейсы с первого дня
- SLO определены до написания кода
- Алерты на деградацию, а не на падение

### P6. Two Contours — Content + Learning

- **Content Contour:** Identity, RAG — кто пользователь, какие знания доступны
- **Learning Contour:** AI Agents, Learning Engine — как обучаем, adaptive path, missions
- Content Contour поставляет данные в Learning Contour (RAG → Designer Agent)
- Learning Contour не модифицирует Content Contour напрямую

### P7. Agent-first architecture

- AI агенты — ядро продукта, не надстройка
- Каждый агент имеет чёткую зону ответственности и контракт (input/output)
- Агенты общаются через Orchestrator, не напрямую
- Телеметрия из Coach → Strategist для адаптации learning path

---

## Architecture Decision Records (ADR)

### ADR-001: Монорепа вместо мультирепо

- [X] ✅ **Решение:** Монорепа (Python + Rust + TypeScript в одном репозитории)
- **Контекст:** Скорость итерации важнее изоляции. Атомарные изменения через границы сервисов
- **Пересмотр:** При > 50 разработчиках оценить переход на мультирепо

### ADR-002: PostgreSQL + pgvector как основная БД

- [X] ✅ **Решение:** PostgreSQL для всех сервисов, pgvector extension для embeddings
- **Контекст:** Один движок БД упрощает operations. pgvector достаточен для < 10M embeddings
- **Дополнительно:** Redis для кэша и agent memory
- **Пересмотр:** При > 10M embeddings или > 100ms vector search — dedicated vector DB

### ADR-003: Application-level multi-tenancy

- [X] ✅ **Решение:** Shared database, org_id фильтрация на application level
- **Контекст:** 1-50 компаний не оправдывают database-per-tenant. Проще в development и operations
- **Защита:** org_id добавляется ко всем запросам через middleware/service layer
- **Пересмотр:** При compliance requirements (SOC2 Type II) — оценить schema-per-tenant

### ADR-004: RAG pipeline в отдельном сервисе

- [X] ✅ **Решение:** RAG как отдельный Python сервис (порт 8008)
- **Контекст:** Ingestion pipeline (chunking, embedding, indexing) — отдельная зона ответственности от AI agents. Разные паттерны нагрузки: batch ingestion vs real-time search
- **Альтернативы:** Встроить в AI service (нарушает SRP), использовать managed RAG (vendor lock-in)

### ADR-005: Tri-Agent orchestration в AI service

- [X] ✅ **Решение:** Strategist, Designer, Coach — модули внутри AI service (порт 8006)
- **Контекст:** Все три агента используют один LLM client, одну Redis memory, один credit system. Разделение на 3 сервиса — преждевременная декомпозиция
- **Паттерн:** Agent Orchestrator координирует вызовы, каждый агент — отдельный module с чётким interface

### ADR-006: FSRS для spaced repetition

- [X] ✅ **Решение:** FSRS (Free Spaced Repetition Scheduler) для recap questions
- **Контекст:** Academically validated, open source (py-fsrs). Переиспользуем из B2C фазы
- **В B2B:** recap questions в начале каждой Mission — spaced repetition по архитектуре компании

### ADR-007: Model routing для AI

- [X] ✅ **Решение:** Multi-tier LLM routing: основной — Gemini Flash, fallback — Claude
- **Контекст:** AI-стоимость ~$2-5/user/month при daily sessions. Mission generation — дешёвая модель. Coach dialogue — средняя. Complex code analysis — дорогая
- **Пересмотр:** При > 1000 daily users — оценить self-hosted SLM

### ADR-008: GitHub adapter для code ingestion

- [X] ✅ **Решение:** GitHub OAuth App + REST API для клонирования и индексации repos
- **Контекст:** GitHub — primary source of truth для большинства tech companies. REST API проще для MVP чем GitHub App
- **Будущее:** GitHub App (webhooks для auto re-index), GitLab adapter, Bitbucket adapter

### ADR-009: Trust Levels вместо XP

- [X] ✅ **Решение:** Trust Level (0-5) с прогрессивным доступом вместо числового XP
- **Контекст:** B2B context: прогресс = доступ к ресурсам компании, не gamification score. Прогрессия привязана к mastery, не к количеству активности
- **Механика:** Mission completion + concept mastery → автоматическое повышение level

### ADR-010: Axum API Gateway для централизованного auth и routing

- [X] ✅ **Решение:** Rust/Axum API Gateway на порту 8080, единая точка входа
- **Контекст:** JWT валидация дублируется в 6 Python сервисах. Next.js rewrites как прокси — дополнительный hop, нет rate limiting. При > 10K RPS Python сервисы становятся bottleneck на auth validation
- **Преимущества:** Централизация JWT, rate limiting (Redis sliding window), CORS, request/response logging, circuit breaker. ~5-10ms overhead. 20K+ RPS на одном инстансе
- **Миграция:** Постепенная — Gateway проксирует трафик параллельно с Next.js rewrites, переключение per-route
- **Пересмотр:** При переходе на K8s — оценить Envoy/Istio vs custom gateway

### ADR-011: pyo3 FFI для CPU-bound RAG operations

- [X] ✅ **Решение:** Rust crate (libs/rs/rag-chunker/) через pyo3+maturin, вызов из Python RAG service
- **Контекст:** Chunking — чистый CPU (regex split, overlap calculation, token counting). Python ~50x медленнее Rust на string processing. Отдельный сервис — overkill, достаточно FFI
- **Преимущества:** 10-50x ускорение chunking, zero-copy где возможно, seamless integration с Python ecosystem
- **Альтернативы:** Отдельный Rust сервис (лишний network hop), Cython (меньший выигрыш), C extension (хуже DX)

### ADR-012: tantivy для full-text search вместо Meilisearch

- [X] ✅ **Решение:** Rust/Axum + tantivy на порту 8010, замена внешней зависимости Meilisearch
- **Контекст:** Meilisearch — внешняя зависимость, ограниченный контроль, 803ms p99 при нагрузке. tantivy — Rust-native FTS engine (аналог Lucene), <50ms p99, полный контроль над индексацией и scoring
- **Пересмотр:** При > 100M документов — оценить Elasticsearch/OpenSearch

---

## Целевая архитектура

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Identity   │     │ Notification │
│  (Next.js)   │     │   (:8001)    │     │   (:8005)    │
│   (:3000)    │     │ + Orgs       │     │              │
└──────┬───────┘     └──────────────┘     └──────────────┘
       │
       ├────────────▶┌──────────────┐     ┌──────────────┐
       │             │  AI Agents   │────▶│     RAG      │
       │             │  (:8006)     │     │   (:8008)    │
       │             │ Strategist   │     │ pgvector     │
       │             │ Designer     │     │ ingestion    │
       │             │ Coach        │     │ search       │
       │             └──────┬───────┘     └──────────────┘
       │                    │
       └────────────▶┌──────▼───────┐
                     │   Learning   │
                     │   (:8007)    │
                     │ Missions     │
                     │ Trust Levels │
                     │ FSRS         │
                     └──────────────┘

Dormant: Course (:8002), Enrollment (:8003), Payment (:8004)
```

### Целевая архитектура (с Rust Performance Layer)

```
┌──────────────┐
│   Frontend   │
│  (Next.js)   │
│   (:3001)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────────────────────────────────────┐
│  API Gateway │     │            RUST PERFORMANCE LAYER             │
│  Axum :8080  │────▶│  Search :8010 (tantivy)                      │
│  JWT, Rate   │     │  Embedding Orchestrator :8009 (tokio batch)   │
│  Limit, CORS │     │  WS Gateway :8011 (real-time)                │
└──────┬───────┘     │  RAG Chunker (pyo3 FFI, no port)             │
       │             └──────────────────────────────────────────────┘
       │
       ├────────────▶ Python services (Identity, AI, Learning, RAG, etc.)
```

### Data flow для daily Mission

```
1. User opens app
2. Frontend → Learning (:8007): GET /missions/daily
3. Learning → AI (:8006): request mission generation
4. AI/Strategist: pick next concept from learning path
5. AI/Designer → RAG (:8008): search company KB for concept content
6. AI/Designer: assemble Mission (recap + reading + questions + code_case)
7. Learning: persist Mission, return to frontend
8. User completes mission with Coach (AI :8006)
9. Coach → Learning: update mastery, check Trust Level progression
```
