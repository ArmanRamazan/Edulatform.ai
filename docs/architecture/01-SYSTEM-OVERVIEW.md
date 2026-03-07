# 01 — System Overview

> Последнее обновление: 2026-03-08

## System Diagram

```
                          ┌─────────────┐     ┌─────────────┐
                          │  buyer:3001  │     │ seller:3002  │
                          │  (Next.js)   │     │  (Next.js)   │
                          └──────┬───────┘     └──────┬───────┘
                                 │                    │
                                 ▼                    ▼
                    ┌────────────────────────────────────┐
                    │      api-gateway:8080 (Rust/axum)  │
                    │      JWT validation + reverse proxy │
                    └──┬──┬──┬──┬──┬──┬──┬──┬──┬────────┘
                       │  │  │  │  │  │  │  │  │
          ┌────────────┘  │  │  │  │  │  │  │  └────────────┐
          ▼               ▼  │  │  │  │  │  ▼               ▼
   ┌──────────┐  ┌─────────┐│  │  │  │  │┌──────────┐ ┌────────┐
   │ identity │  │  course  ││  │  │  │  ││   rag    │ │ search │
   │  :8001   │  │  :8002   ││  │  │  │  ││  :8008   │ │ :9000  │
   └────┬─────┘  └────┬─────┘│  │  │  │  │└────┬─────┘ └────────┘
        │              │      │  │  │  │  │     │        (Rust/
     [5433]         [5434]    │  │  │  │  │  [5439]      tantivy)
                              ▼  │  │  │  ▼
                    ┌──────────┐ │  │  │ ┌──────────────┐
                    │enrollment│ │  │  │ │ notification  │
                    │  :8003   │ │  │  │ │    :8005      │
                    └────┬─────┘ │  │  │ └──────┬────────┘
                      [5435]     │  │  │      [5437]
                                 ▼  │  ▼
                       ┌──────────┐ │ ┌──────────┐
                       │ payment  │ │ │    ai    │
                       │  :8004   │ │ │  :8006   │
                       └────┬─────┘ │ └──────────┘
                         [5436]     │  (no DB,
                                    ▼   Gemini API)
                          ┌──────────┐
                          │ learning │
                          │  :8007   │
                          └────┬─────┘
                            [5438]

                    ┌──────────────────┐
                    │   Redis :6379    │
                    │ (cache, sessions)│
                    └──────────────────┘

          ┌───────────────────┐   ┌──────────────────────────┐
          │ ws-gateway :8011  │   │ embedding-orchestrator   │
          │ (Rust, WebSocket) │   │ :8009 (Rust, Gemini API) │
          └───────────────────┘   └──────────────────────────┘
```

## Service Inventory

| Service | Language | Framework | Port | DB Port | Tests | Purpose |
|---------|----------|-----------|------|---------|-------|---------|
| api-gateway | Rust | axum | 8080 | — | cargo test | JWT validation, Redis rate limiting (100/min auth, 20/min unauth), reverse proxy to all backends |
| ws-gateway | Rust | axum | 8011 | — | cargo test | WebSocket real-time notifications |
| embedding-orchestrator | Rust | axum | 8009 | — | cargo test | Concurrent embedding API proxy |
| identity | Python | FastAPI | 8001 | 5433 | 156 | Auth, users, profiles, follows, referrals, organizations |
| course | Python | FastAPI | 8002 | 5434 | 129 | Courses, modules, lessons, reviews, bundles, promotions, wishlist, categories, analytics |
| enrollment | Python | FastAPI | 8003 | 5435 | 39 | Enrollments, lesson progress, recommendations |
| payment | Python | FastAPI | 8004 | 5436 | 190 | Payments, subscriptions, earnings, coupons, refunds, gifts, org subscriptions, MockStripeClient |
| notification | Python | FastAPI | 8005 | 5437 | 145 | Notifications, streak/flashcard reminders, direct messaging, StubEmailClient |
| ai | Python | FastAPI | 8006 | — | 291 | LLM orchestrator (Gemini Flash), tri-agent coaching, missions, credits, unified search, MockLLMProvider |
| learning | Python | FastAPI | 8007 | 5438 | 272 | Quizzes, flashcards (FSRS), concepts, streaks, leaderboard, discussions, XP, badges, pretests, velocity, activity feed, study groups, missions, daily summary, certificates, trust levels |
| rag | Python | FastAPI | 8008 | 5439 | 180 | pgvector, document ingestion, semantic search, concept extraction, GitHub adapter, KB management, StubEmbeddingClient |
| search | Rust | axum + tantivy | 9000 | — | cargo test | Full-text search index |

## Frontend

| App | Port | Framework | Purpose |
|-----|------|-----------|---------|
| buyer | 3001 | Next.js 15 + React 19 + Tailwind + shadcn/ui | B2B knowledge platform (Dark Knowledge theme) |
| seller | 3002 | Next.js 15 + React 19 + TanStack Query | Teacher dashboard |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Python runtime | 3.12 |
| Python framework | FastAPI + uvicorn |
| Rust runtime | tokio |
| Rust HTTP | axum |
| Rust search | tantivy |
| Rust FFI | PyO3 (rag-chunker) |
| Database | PostgreSQL 16 (asyncpg) |
| Vectors | pgvector (768-dim embeddings) |
| Cache | Redis 7 |
| Frontend | Next.js 15 (App Router), React 19, TypeScript strict |
| UI | Tailwind CSS, shadcn/ui (Radix), Lucide icons |
| State | TanStack Query (server), Zustand (client) |
| Auth | JWT HS256 (bcrypt passwords) |
| LLM | Gemini Flash (via google-generativeai) |
| Monitoring | Prometheus + Grafana |
| Package mgmt | uv (Python), pnpm (JS), cargo (Rust) |
| Containers | Docker Compose (dev/prod/staging) |

## Communication

All client requests go through the Rust **api-gateway** which validates JWT, enforces Redis-backed rate limiting, and reverse-proxies to the appropriate Python service based on URL prefix. Rate limiting is keyed by `user_id` for authenticated requests (100 req/min) and by IP for unauthenticated requests (20 req/min). Services do not call each other directly — they operate on their own data within their bounded context.

## Testing

**Total: 1402 tests passed, 6 pre-existing failures** across 8 Python + 4 Rust services.

```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
cd services/rs/<name> && cargo test && cargo clippy -- -D warnings
cd libs/rs/rag-chunker && cargo test && cargo clippy -- -D warnings
```
