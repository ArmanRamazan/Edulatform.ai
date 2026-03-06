# Phase 3 — B2B Growth [COMPLETED]

> **Статус:** ЗАВЕРШЕНА
>
> Пивот от B2C course marketplace к B2B AI-powered engineering onboarding.

## Что было построено

### B2B Foundation
- **Organizations** — CRUD организаций, memberships, multi-tenant (identity service)
- **Org Subscriptions** — pilot/starter/growth/enterprise тиры через Stripe (payment service)
- **Trust Levels** — B2B рейтинг участников 1–5 (learning service)

### RAG Service (port 8008, 173 теста)
- Document ingestion (file, github, url, text)
- pgvector semantic search (768-dim embeddings)
- Concept extraction via LLM
- Knowledge base management per org
- **GitHub adapter** — загрузка файлов из репозиториев
- **Rust rag-chunker** — PyO3 FFI crate для markdown-aware chunking с Python fallback

### AI Service расширения
- **Tri-agent coaching**: Strategist → Designer → Coach pipeline
- **Missions**: daily/complete с AI coach sessions
- **Unified search**: query router (internal RAG + external Gemini)
- **LLM config**: per-org настройка провайдеров (admin)
- **Credits system**: лимиты по тарифу подписки

### Search Service (Rust, port 9000)
- Tantivy full-text search
- Batch indexing
- Per-org index isolation

### Buyer App (Dark Knowledge Theme)
- Dashboard с 7 блоками (Greeting, Mission, TrustLevel, Flashcards, Mastery, Activity, TeamProgress)
- Concept Hub — Obsidian-like страница концепта (sources, missions, discussions, team mastery)
- Smart Search — unified search с route indicator
- Mission Sessions — 5-phase coach UI (recap → reading → questions → code_case → wrap_up)
- Flashcards page
- Team Analytics — heatmap coverage, bottleneck reports
- Billing — Stripe subscription management
- Dark-first UI: violet accent (#7c5cfc), Inter + JetBrains Mono

### Тесты
- RAG: 173 новых тестов
- Org endpoints, missions, trust levels: ~150 дополнительных

## Результат

Полноценная B2B платформа: организации, RAG knowledge base, AI coaching, unified search, dark knowledge UI. **1343 тестов, 10 сервисов.**
