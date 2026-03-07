# KnowledgeOS — The Operating System for Engineering Knowledge

> Your company's code is the curriculum. AI builds the lessons.

B2B AI-powered knowledge platform for engineering team onboarding. Turns codebases and documentation into a living knowledge graph with personalized AI coaching.

## Architecture

Monorepo: **Python** (business logic) + **Rust** (performance-critical) + **TypeScript/Next.js** (frontend).

| Service | Lang | Port | Tests | Purpose |
|---------|------|------|-------|---------|
| api-gateway | Rust | 8080 | + | JWT proxy, routing |
| ws-gateway | Rust | 8011 | + | WebSocket real-time notifications |
| embedding-orchestrator | Rust | 8009 | + | Concurrent embedding API proxy |
| identity | Python | 8001 | 156 | Auth, profiles, organizations |
| course | Python | 8002 | 129 | Courses, modules, lessons, reviews, bundles |
| enrollment | Python | 8003 | 39 | Enrollments, progress |
| payment | Python | 8004 | 190 | Payments, subscriptions, earnings, gifts, org billing, MockStripeClient |
| notification | Python | 8005 | 145 | Notifications, messaging, StubEmailClient |
| ai | Python | 8006 | 291 | LLM orchestrator, tri-agent coaching, missions, unified search, MockLLMProvider |
| learning | Python | 8007 | 272 | Quizzes, flashcards (FSRS), concepts, gamification, certificates, trust levels |
| rag | Python | 8008 | 180 | pgvector, ingestion, semantic search, concept extraction, GitHub adapter |
| search | Rust | 9000 | + | Full-text search (tantivy) |

**Frontend**: buyer (Next.js 15, port 3001, 28 pages) + seller (Next.js 15, port 3002)

**Total: 1402 tests passed, 6 pre-existing failures** across 8 Python services.

## Quick Start

```bash
cp .env.example .env                                      # Configure env vars
docker compose -f docker-compose.dev.yml up -d --build    # All backends + DBs
docker compose -f docker-compose.dev.yml --profile seed up seed  # Seed demo data
cd apps/buyer && pnpm install && pnpm dev                 # http://localhost:3001

# Demo login: demo@acme.com / demo123
```

## Mock Mode (no API keys required)

| Dependency | Without key | Behavior |
|------------|-------------|----------|
| Gemini API (`GEMINI_API_KEY`) | MockLLMProvider | AI returns realistic mock responses |
| Stripe (`STRIPE_SECRET_KEY`) | MockStripeClient | Payments return fake success data |
| Resend (`RESEND_API_KEY`) | StubEmailClient | Emails logged but not sent |
| Embeddings (`GEMINI_API_KEY`) | StubEmbeddingClient | Random vectors (search degraded) |

## Testing

```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
cd services/rs/<name> && cargo test && cargo clippy -- -D warnings
```

## Documentation

- [Technical Overview](docs/TECHNICAL-OVERVIEW.md)
- [System Overview](docs/architecture/01-SYSTEM-OVERVIEW.md)
- [API Reference](docs/architecture/02-API-REFERENCE.md)
- [Database Schemas](docs/architecture/03-DATABASE-SCHEMAS.md)
- [Auth Flow](docs/architecture/04-AUTH-FLOW.md)
- [Infrastructure](docs/architecture/05-INFRASTRUCTURE.md)
- [Shared Libraries](docs/architecture/06-SHARED-LIBRARY.md)

## Tech Stack

Python 3.12 (FastAPI) | Rust (axum, tantivy, PyO3) | Next.js 15 (React 19, Tailwind, shadcn/ui) | PostgreSQL 16 | pgvector | Redis 7 | Gemini Flash | Prometheus + Grafana | Docker Compose
