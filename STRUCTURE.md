# Monorepo Structure

> YAGNI — только то, что используется. SRP — один сервис = один домен.

```
.
├── apps/
│   ├── buyer/                    # Next.js 15 — B2B knowledge platform (port 3001)
│   │   ├── app/
│   │   │   ├── (app)/            # Authenticated pages (sidebar layout)
│   │   │   │   ├── dashboard/    # 7-block dashboard
│   │   │   │   ├── search/       # Smart search (RAG + external)
│   │   │   │   ├── flashcards/   # FSRS spaced repetition
│   │   │   │   ├── missions/[id]/ # Coach session
│   │   │   │   ├── graph/[id]/   # Concept hub
│   │   │   │   ├── settings/     # Analytics, billing
│   │   │   │   └── ...
│   │   │   └── (marketing)/      # Public pages (landing, auth)
│   │   ├── components/           # 71 components (ui/, layout/, dashboard/, graph/, mission/, search/, admin/)
│   │   ├── hooks/                # 28 custom hooks (use-auth, use-coach, use-flashcards, ...)
│   │   └── lib/                  # api.ts (typed API client), utils.ts
│   │
│   └── seller/                   # Next.js 15 — Teacher dashboard (port 3002)
│       ├── app/                  # Dashboard, course CRUD
│       ├── components/
│       └── lib/
│
├── services/
│   ├── py/
│   │   ├── identity/             # Port 8001, DB 5433 — Auth, profiles, orgs
│   │   │   ├── app/
│   │   │   │   ├── routes/       # auth, profiles, follows, referrals, organizations, admin
│   │   │   │   ├── services/
│   │   │   │   ├── domain/
│   │   │   │   └── repositories/
│   │   │   ├── migrations/       # 010 migrations
│   │   │   └── tests/            # 156 tests
│   │   │
│   │   ├── course/               # Port 8002, DB 5434 — Courses, modules, lessons [B2C LEGACY — not used in B2B flow]
│   │   │   ├── app/routes/       # courses, modules, lessons, reviews, bundles, promotions, wishlist, categories, analytics
│   │   │   ├── migrations/       # 010 migrations
│   │   │   └── tests/            # 129 tests
│   │   │
│   │   ├── enrollment/           # Port 8003, DB 5435 — Enrollments, progress [B2C LEGACY — not used in B2B flow]
│   │   │   ├── app/routes/       # enrollments, progress, recommendations
│   │   │   ├── migrations/       # 004 migrations
│   │   │   └── tests/            # 39 tests
│   │   │
│   │   ├── payment/              # Port 8004, DB 5436 — Payments, subscriptions
│   │   │   ├── app/routes/       # payments, coupons, earnings, refunds, gifts, invoices, org_subscriptions
│   │   │   ├── migrations/       # 008 migrations
│   │   │   └── tests/            # 190 tests
│   │   │
│   │   ├── notification/         # Port 8005, DB 5437 — Notifications, messaging
│   │   │   ├── app/routes/       # notifications, messaging
│   │   │   ├── migrations/       # 010 migrations
│   │   │   └── tests/            # 191 tests
│   │   │
│   │   ├── ai/                   # Port 8006 — LLM orchestrator
│   │   │   ├── app/routes/       # ai, coach, orchestrator, search, llm_config
│   │   │   └── tests/            # 316 tests
│   │   │
│   │   ├── learning/             # Port 8007, DB 5438 — Learning engine
│   │   │   ├── app/routes/       # quizzes, flashcards, concepts, missions, streaks, leaderboard, discussions, study_groups, xp, badges, certificates, pretests, trust_levels, velocity, activity, daily
│   │   │   ├── migrations/       # 015 migrations
│   │   │   └── tests/            # 324 tests
│   │   │
│   │   ├── rag/                  # Port 8008, DB 5439 — RAG & knowledge base
│   │   │   ├── app/routes/       # ingestion, search, knowledge_base, concepts, github
│   │   │   ├── migrations/       # 002 migrations
│   │   │   └── tests/            # 230 tests
│   │   │
│   │   └── mcp/                  # MCP server — AI agent tool interface
│   │       ├── app/
│   │       │   ├── client.py     # PlatformClient: typed HTTP wrapper to api-gateway
│   │       │   ├── config.py     # Settings (MCP_API_BASE_URL, MCP_AUTH_TOKEN)
│   │       │   ├── main.py       # FastMCP entry point
│   │       │   └── tools.py      # register_tools, register_knowledge_tools, register_resources
│   │       └── tests/            # 59 tests
│   │
│   └── rs/
│       ├── api-gateway/          # Port 8080 — Rust reverse proxy (axum, JWT)
│       │   ├── src/              # main.rs, config.rs, routes/
│       │   └── tests/
│       │
│       ├── ws-gateway/           # Port 8011 — WebSocket real-time (axum)
│       │   └── src/
│       └── embedding-orchestrator/ # Port 8009 — Concurrent embedding proxy (axum)
│           └── src/
│
├── libs/
│   ├── py/
│   │   └── common/              # Shared Python: errors, security (JWT), database (asyncpg), config, logging
│   └── rs/
│       └── rag-chunker/         # PyO3 FFI: markdown-aware chunking
│
├── deploy/
│   ├── docker/                  # Dockerfiles per service, Grafana dashboards, Prometheus config
│   ├── scripts/                 # backup-all-dbs.sh, restore-db.sh, list-backups.sh
│   └── staging/                 # .env.staging.example
│
├── tools/
│   ├── orchestrator/            # Autonomous Claude Code task executor
│   ├── seed/                    # Database seed script
│   │   └── demo_documents/      # 5 technical MD docs seeded into RAG service
│   ├── locust/                  # Load testing (locustfile.py)
│   └── demo/                    # Demo script
│
├── docs/
│   ├── architecture/            # 01-06: system, API, DB, auth, infra, libs
│   ├── phases/                  # PHASE-0 through PHASE-5
│   ├── goals/                   # Product vision, architecture principles, domains
│   └── ...
│
├── docker-compose.dev.yml       # Development (hot reload)
├── docker-compose.prod.yml      # Production (monitoring, 4 workers)
├── docker-compose.staging.yml   # Staging (pre-built images)
├── pyproject.toml               # uv workspace root
├── pnpm-workspace.yaml          # pnpm workspace
└── turbo.json                   # Turborepo config
```

## Service Architecture (Python)

```
services/py/{name}/
├── app/
│   ├── routes/          # HTTP handlers (parse request → call service → format response)
│   ├── services/        # Use cases (orchestrate domain + repositories)
│   ├── domain/          # Entities, Value Objects (pure Python, no framework imports)
│   └── repositories/    # ABC interface + SQL implementation
├── migrations/          # Idempotent SQL (forward-only)
├── tests/               # Unit (AsyncMock) + integration
└── pyproject.toml       # Virtual workspace member
```

Dependency rule: `routes → services → domain ← repositories`
