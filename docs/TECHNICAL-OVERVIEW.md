# KnowledgeOS — Technical Overview

B2B AI-powered knowledge platform for engineering team onboarding via knowledge graph and AI coaching.

## Architecture

Monorepo: **Python** (business logic) + **Rust** (performance-critical) + **TypeScript/Next.js** (frontend).

Clean Architecture in every Python service: `routes → services → domain ← repositories`. Each service owns its PostgreSQL database. No cross-service DB access.

## Services

| Service | Language | Framework | Port | DB Port | Tests | Purpose |
|---------|----------|-----------|------|---------|-------|---------|
| api-gateway | Rust | axum | 8000 | — | cargo test | JWT validation, reverse proxy |
| identity | Python | FastAPI | 8001 | 5433 | 156 | Auth, profiles, follows, referrals, organizations |
| course | Python | FastAPI | 8002 | 5434 | 129 | Courses, modules, lessons, reviews, bundles, promotions, wishlist |
| enrollment | Python | FastAPI | 8003 | 5435 | 39 | Enrollments, lesson progress, recommendations |
| payment | Python | FastAPI | 8004 | 5436 | 190 | Payments, subscriptions, earnings, coupons, refunds, gifts, org billing, MockStripeClient |
| notification | Python | FastAPI | 8005 | 5437 | 145 | Notifications, reminders, direct messaging, StubEmailClient |
| ai | Python | FastAPI | 8006 | — | 291 | LLM orchestrator (Gemini Flash), tri-agent coaching, missions, unified search, MockLLMProvider fallback, SSE coach streaming |
| learning | Python | FastAPI | 8007 | 5438 | 272 | Quizzes, flashcards (FSRS), concepts, streaks, leaderboard, discussions, XP, badges, pretests, velocity, activity, study groups, missions, certificates, trust levels |
| rag | Python | FastAPI | 8008 | 5439 | 180 | pgvector, document ingestion, semantic search, concept extraction, GitHub adapter, StubEmbeddingClient |
| mcp | Python | FastMCP | — | — | 59 | MCP server exposing KB tools for AI agents (Claude, Cursor); auth via Bearer token to api-gateway |
| ws-gateway | Rust | axum | 8011 | — | cargo test | WebSocket real-time notifications |
| embedding-orchestrator | Rust | axum | 8009 | — | cargo test | Concurrent embedding API proxy |
| search | Rust | axum + tantivy | 9000 | — | cargo test | Full-text search index |

**Total: 1461 tests passed, 6 pre-existing failures** (3 enrollment, 3 notification).

## Frontend

| App | Port | Stack | Purpose |
|-----|------|-------|---------|
| buyer | 3001 | Next.js 15, React 19, Tailwind, shadcn/ui, TanStack Query | B2B knowledge platform (dashboard, missions, concept hub, smart search, flashcards, coach) |
| seller | 3002 | Next.js 15, React 19, TanStack Query | Teacher dashboard (course CRUD) |

Buyer app: 28 pages (dashboard, onboarding, graph, search, missions, flashcards, notifications, badges, feed, velocity, messages, groups, settings, admin, org select, auth pages).

Buyer theme: Dark-first UI, violet accent (#7c5cfc), Inter + JetBrains Mono fonts.

## Mock Mode (Demo without API keys)

| External Dependency | Env Var | Without key |
|---------------------|---------|-------------|
| Gemini LLM | `GEMINI_API_KEY` | `MockLLMProvider` — realistic mock responses |
| Stripe | `STRIPE_SECRET_KEY` | `MockStripeClient` — fake success data |
| Resend email | `RESEND_API_KEY` | `StubEmailClient` — emails logged only |
| Gemini Embeddings | `GEMINI_API_KEY` | `StubEmbeddingClient` — random vectors |

## Shared Libraries

| Library | Language | Purpose |
|---------|----------|---------|
| `libs/py/common` | Python | Errors, JWT (create/decode with extra_claims), async DB pool (asyncpg), config (pydantic BaseSettings), structured logging |
| `libs/rs/rag-chunker` | Rust (PyO3) | Markdown-aware chunking FFI crate with Python fallback |

## Authentication

JWT HS256 tokens. Claims: `sub` (user_id), `role` (student/teacher/admin), `is_verified`, `email_verified`, `organization_id` (B2B), `subscription_tier`.

- Access token: 1h TTL. Refresh token: 30d TTL (stored in DB, revocable)
- API gateway validates JWT and proxies to upstream services
- Passwords: bcrypt hash

## B2B Multi-Tenancy

- Organizations with members and roles
- `organization_id` in JWT extra_claims
- Services filter data by org_id
- Org subscriptions: pilot / starter / growth / enterprise tiers (Stripe)
- Per-org LLM configuration
- Trust levels per org member

## AI Pipeline

Tri-agent coaching system powered by Gemini Flash:

1. **Strategist** — analyzes learner state, selects concept and difficulty
2. **Designer** — creates mission blueprint (phases: recap → reading → questions → code_case → wrap_up)
3. **Coach** — conducts interactive session with the learner

Additional: quiz generation, summary generation, course outline, lesson generation, tutor chat, content moderation, unified search (query router: internal RAG + external Gemini).

## Knowledge Graph

- **Concepts** with prerequisites (directed graph) in learning service
- **Concept mastery** (0.0–1.0) tracked per student per concept
- **RAG concepts** extracted from documents via LLM in rag service
- **Concept hub** UI: Obsidian-like page with internal sources, missions, discussions, team mastery

## Gamification

XP points, badges, streaks, leaderboard (per course, opt-in), trust levels (B2B, 1–5), certificates.

## Infrastructure

| Component | Version | Purpose |
|-----------|---------|---------|
| PostgreSQL | 16-alpine | Primary database (7 instances) |
| Redis | 7-alpine | Cache, rate limiting |
| Prometheus | latest | Metrics (5s scrape, 15d retention) |
| Grafana | latest | Dashboards (auto-provisioned) |

Docker Compose: dev (hot reload), prod (4-worker uvicorn + monitoring), staging (pre-built images).

## Development

```bash
docker compose -f docker-compose.dev.yml up                          # All backends + DBs
docker compose -f docker-compose.dev.yml --profile seed up seed      # Seed data
cd apps/buyer && pnpm dev                                            # Frontend (3001)
cd apps/seller && pnpm dev                                           # Seller (3002)
cd services/py/<name> && uv run --package <name> pytest tests/ -v    # Python tests
cd services/rs/<name> && cargo test && cargo clippy -- -D warnings   # Rust tests
```
