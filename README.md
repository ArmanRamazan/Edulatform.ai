# KnowledgeOS — The Operating System for Engineering Knowledge

> Your company's code is the curriculum. AI builds the lessons.

**Every engineering team has the same problem:** documentation is outdated, onboarding takes months, and critical knowledge lives in one person's head. KnowledgeOS fixes this by turning your codebase and docs into a living, AI-powered knowledge graph that teaches itself.

```
      ┌──────────────────────────────────────────────────────────────┐
      │                                                              │
      │    Your Code + Docs                                          │
      │         │                                                    │
      │         ▼                                                    │
      │    ┌─────────────┐     ┌──────────────┐    ┌────────────┐   │
      │    │  RAG Engine  │────▶│  AI Strategist│───▶│  Knowledge │   │
      │    │  (pgvector)  │     │  (Gemini)     │    │   Graph    │   │
      │    └─────────────┘     └──────────────┘    └─────┬──────┘   │
      │                                                   │          │
      │         ┌─────────────────────────────────────────┘          │
      │         ▼                                                    │
      │    ┌──────────┐    ┌──────────────┐    ┌─────────────────┐  │
      │    │ Designer │───▶│ Daily Mission │───▶│  Socratic Coach │  │
      │    │ (builds)  │    │ (personalized)│    │  (teaches)      │  │
      │    └──────────┘    └──────────────┘    └─────────────────┘  │
      │                                                              │
      │    Result: Engineer masters your stack in weeks, not months  │
      └──────────────────────────────────────────────────────────────┘
```

## The Problem

- **87% of engineering onboarding is passive** — reading docs, watching recordings, shadowing
- **Average time to first meaningful commit: 3 months** at large companies
- **Knowledge silos** — when senior engineers leave, knowledge walks out the door
- Internal wikis are where documentation goes to die

## How It Works

**1. Ingest** — Connect your GitHub repos, upload docs, or paste markdown. RAG engine chunks, embeds, and extracts concepts automatically.

**2. Map** — AI builds a knowledge graph of your stack. Concepts, dependencies, difficulty levels — all visible in an interactive Obsidian-like graph.

**3. Learn** — Tri-agent AI system creates personalized daily missions:
- **Strategist** plans your learning path through the concept graph
- **Designer** assembles missions from your actual code and docs
- **Coach** teaches through Socratic dialogue — never gives answers, always asks the right questions

**4. Grow** — Trust Level system (0-5) progressively unlocks access as engineers prove mastery. From documentation → staging → production → architecture decisions.

## Why This Architecture

```
Python (8 services)          — business logic, AI orchestration, CRUD
Rust (3 services, planned)   — API gateway, search, real-time messaging
Next.js (App Router)         — Dark Knowledge UI (Obsidian-inspired)
PostgreSQL (7 databases)     — one per service, full isolation
pgvector                     — semantic search, RAG embeddings
Redis                        — session cache, rate limiting, agent memory
Gemini Flash                 — quiz generation, coaching, content design
FSRS algorithm               — spaced repetition, scientifically optimal intervals
```

## Numbers

| Metric | Value |
|--------|-------|
| Backend services | **8** (Identity, Course, Enrollment, Payment, Notification, AI, Learning, RAG) |
| Unit tests | **1216** |
| API endpoints | **130+** |
| Database tables | **45+** |
| AI agents | **3** (Strategist, Designer, Coach) |
| Trust levels | **6** (Observer → Expert) |
| Data isolation | **Configurable per org** (Gemini or self-hosted LLM) |

## Smart Search with Data Isolation

Two search channels that never cross:

```
"How does our auth middleware work?"
  → INTERNAL ONLY → RAG search → your company's code
  → Results never leave your infrastructure

"React Suspense best practices"
  → EXTERNAL ONLY → Gemini web grounding → public internet
  → Only query text sent, zero internal context

"How we implemented caching and best practices"
  → BOTH (parallel) → RAG + Web → results merged on frontend only
  → Internal data and external queries in separate API calls
```

Configurable per organization: **Standard** (Gemini processes internal data under ToS) or **Strict** (self-hosted LLM, nothing leaves your infra).

## MCP-Ready

Every user-facing endpoint is designed for AI tool integration. Connect KnowledgeOS to Cursor, Claude Desktop, or your custom agent:

```
search_knowledge  — semantic search across your KB
get_concept_graph — full knowledge graph with mastery
start_mission     — begin today's learning session
coach_chat        — Socratic dialogue with AI coach
create_concept    — add to the knowledge graph
```

16 MCP tools. Full CRUD. JWT-authenticated. Trust level enforced.

## Quick Start

```bash
# Backend (all 8 services + databases)
docker compose -f docker-compose.dev.yml up

# Frontend (Dark Knowledge UI)
cd apps/buyer && pnpm install && pnpm dev

# Seed test data
docker compose -f docker-compose.dev.yml --profile seed up seed

# Run all 1216 tests
cd services/py/identity    && uv run --package identity pytest tests/ -v
cd services/py/course      && uv run --package course pytest tests/ -v
cd services/py/enrollment  && uv run --package enrollment pytest tests/ -v
cd services/py/payment     && uv run --package payment pytest tests/ -v
cd services/py/notification && uv run --package notification pytest tests/ -v
cd services/py/ai          && uv run --package ai pytest tests/ -v
cd services/py/learning    && uv run --package learning pytest tests/ -v
cd services/py/rag         && uv run --package rag pytest tests/ -v
```

## AI Orchestrator

Autonomous build system. Reads YAML task files, executes via Claude Code CLI, runs tests, commits. Multi-agent mode parallelizes independent tasks.

```bash
cd tools/orchestrator

# Run a sprint (multi-agent, parallel where possible)
./run.sh tasks/sprint-21-dark-knowledge-foundation.yaml --multi-agent

# Full B2B pipeline (all sprints, auto-parallelized)
./run-b2b.sh

# Preview without executing
./run-b2b.sh --dry-run

# Resume after interruption
./run-b2b.sh --resume
```

## Documentation

- [Design Document](docs/plans/2026-03-05-b2b-knowledge-platform-design.md) — Dark Knowledge theme, concept hub, MCP server
- [Technical Overview](docs/TECHNICAL-OVERVIEW.md) — stack, ports, structure, quickstart
- [AI Agent Standards](docs/goals/11-AI-AGENT-STANDARDS.md) — tri-agent system, data isolation, MCP readiness
- [Architecture](docs/architecture/01-SYSTEM-OVERVIEW.md) — system diagram, service boundaries

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| **Foundation** | 8 Python services, Clean Architecture, 1216 tests | Done |
| **Learning Intelligence** | AI agents, FSRS, knowledge graph, gamification | Done |
| **B2B Pivot** | Dark Knowledge UI, org isolation, smart search, MCP | Sprint 21 ✅ · Sprint 22 next |
| **Rust Performance** | API gateway, search service, WebSocket, embedding orchestrator | Planned |
| **Scale** | 10M users, multi-region, self-hosted LLM option | Planned |

---

Built with obsessive attention to architecture. Every service has its own database. Every endpoint is tested. Every AI interaction respects data boundaries. No shortcuts.
