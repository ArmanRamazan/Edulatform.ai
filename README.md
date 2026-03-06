# KnowledgeOS — The Operating System for Engineering Knowledge

> Your company's code is the curriculum. AI builds the lessons.

B2B AI-powered knowledge platform for engineering team onboarding. Turns codebases and documentation into a living knowledge graph with personalized AI coaching.

## Architecture

Monorepo: **Python** (business logic) + **Rust** (performance-critical) + **TypeScript/Next.js** (frontend).

| Service | Lang | Port | Tests | Purpose |
|---------|------|------|-------|---------|
| api-gateway | Rust | 8000 | + | JWT proxy, routing |
| identity | Python | 8001 | 156 | Auth, profiles, organizations |
| course | Python | 8002 | 129 | Courses, modules, lessons, reviews, bundles |
| enrollment | Python | 8003 | 39 | Enrollments, progress |
| payment | Python | 8004 | 151 | Payments, subscriptions, earnings, gifts, org billing |
| notification | Python | 8005 | 136 | Notifications, messaging |
| ai | Python | 8006 | 291 | LLM orchestrator, tri-agent coaching, missions, unified search, MockLLMProvider, SSE streaming |
| learning | Python | 8007 | 272 | Quizzes, flashcards, concepts, gamification, certificates |
| rag | Python | 8008 | 173 | pgvector, ingestion, semantic search, concept extraction |
| search | Rust | 9000 | + | Full-text search (tantivy) |

**Frontend**: buyer (Next.js 15, port 3001) + seller (Next.js 15, port 3002)

**Total: 1357 tests passed** across 10 services.

## Quick Start

```bash
# Start all backends + databases
docker compose -f docker-compose.dev.yml up

# Seed test data
docker compose -f docker-compose.dev.yml --profile seed up seed

# Frontend
cd apps/buyer && pnpm install && pnpm dev    # http://localhost:3001
cd apps/seller && pnpm install && pnpm dev   # http://localhost:3002
```

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
