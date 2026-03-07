# 05 — Infrastructure

> Последнее обновление: 2026-03-08

## Docker Compose

Три конфигурации:

| Config | Command | Purpose |
|--------|---------|---------|
| `docker-compose.dev.yml` | `docker compose -f docker-compose.dev.yml up` | Hot reload, debug ports, single-worker |
| `docker-compose.prod.yml` | `docker compose -f docker-compose.prod.yml up -d` | 4-worker uvicorn, monitoring, health checks |
| `docker-compose.staging.yml` | `docker compose -f docker-compose.staging.yml up -d` | Pre-built images, staging DB ports |

## Databases

PostgreSQL 16-alpine. Каждый сервис — своя БД:

| Service | DB Name | Image | Dev Port | Staging Port |
|---------|---------|-------|----------|-------------|
| identity | identity | postgres:16-alpine | 5433 | 5443 |
| course | course | postgres:16-alpine | 5434 | 5444 |
| enrollment | enrollment | postgres:16-alpine | 5435 | 5445 |
| payment | payment | postgres:16-alpine | 5436 | 5446 |
| notification | notification | postgres:16-alpine | 5437 | 5447 |
| learning | learning | postgres:16-alpine | 5438 | 5448 |
| rag | rag | **pgvector/pgvector:pg16** | 5439 | — |

> `rag-db` использует `pgvector/pgvector:pg16` (не plain postgres) — требует расширение `vector` для хранения эмбеддингов.

**Redis 7-alpine** на порту 6379 — кэш, сессии и rate limiting.

Rate limiting (api-gateway): INCR + EXPIRE pattern, ключи вида `rl:user:{uid}:{group}:{window_ts}` (auth) и `rl:ip:{ip}:{group}:{window_ts}` (unauth). Fail-open при недоступности Redis.

**NATS 2.10-alpine** — async event bus между доменами (JetStream):

| Port | Purpose |
|------|---------|
| 4222 | Client connections (all services) |
| 8222 | HTTP monitoring (`/healthz`, Prometheus scrape target) |

Stream: `PLATFORM_EVENTS`, subjects: `platform.mastery.updated`, `platform.mission.completed`, `platform.badge.earned`, `platform.streak.milestone`. Storage: file (события переживают рестарт контейнера). Max age: 72h.

Клиентская обёртка: `common.nats.NATSClient` (фабрика `create_nats_client(url)`). Env var: `NATS_URL=nats://nats:4222` — инжектируется во все Python-сервисы.

## Dockerfiles

Расположение: `deploy/docker/{service}.Dockerfile`

Паттерн для Python сервисов:
```dockerfile
FROM python:3.12-slim

# uv через GitHub release (не COPY --from= — ломается на WSL2)
ADD https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN tar -xzf /tmp/uv.tar.gz -C /tmp && mv /tmp/uv-x86_64-unknown-linux-gnu/uv /bin/uv

WORKDIR /app
COPY libs/py/common /libs/common
COPY services/py/{service}/pyproject.toml .
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv /libs/common && \
    uv pip install --python /app/.venv <deps>

ENV PATH="/app/.venv/bin:$PATH"
COPY services/py/{service}/ .
EXPOSE 800X
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "800X"]
```

Production override: `--workers 4 --timeout-graceful-shutdown 25`

Паттерн для Rust сервисов:
```dockerfile
FROM rust:1.88-slim AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo 'fn main() {}' > src/main.rs
RUN cargo build --release && rm -rf src
COPY src/ src/
RUN touch src/main.rs && cargo build --release

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /app/target/release/{binary} /usr/local/bin/
```

> Rust сервисы требуют `Cargo.lock` рядом с `Cargo.toml` (генерируется через `cargo generate-lockfile`).
> Версия `rust:1.88-slim` — минимум для зависимостей (time v0.3.47+ требует Rust 1.88.0).

## Monitoring (Production)

### Prometheus (port 9090)
- Scrapes все 8 Python сервисов + api-gateway
- Интервал: 5s, retention: 15d
- Config: `deploy/docker/prometheus/prometheus.yml`
- Каждый Python сервис экспортирует `/metrics` через `prometheus-fastapi-instrumentator`

### Grafana (port 3000)
- Auto-provisioned datasources и dashboards
- Anonymous access (no login)
- Dashboards: `deploy/docker/grafana/dashboards/services.json`
- Config: `deploy/docker/grafana/provisioning/`

## Health Checks

Production compose включает health checks для каждого сервиса:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:800X/health"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 15s
```

API Gateway: `GET /health/live`, `GET /health/ready`

## Backup & Restore

| Script | Purpose |
|--------|---------|
| `deploy/scripts/backup-all-dbs.sh` | Параллельный pg_dump всех 7 БД → `deploy/backups/` |
| `deploy/scripts/restore-db.sh` | Восстановление из бэкапа (требует `--confirm`) |
| `deploy/scripts/list-backups.sh` | Список доступных бэкапов |

```bash
# Backup
./deploy/scripts/backup-all-dbs.sh

# Restore
./deploy/scripts/restore-db.sh identity deploy/backups/identity-2026-03-06.sql.gz --confirm
```

## Environment Variables

### Required

| Variable | Service | Description |
|----------|---------|-------------|
| `JWT_SECRET` | all | JWT signing secret (64+ chars) |
| `{SERVICE}_DATABASE_URL` | per service | PostgreSQL connection string |
| `REDIS_URL` | all | Redis connection (default: redis://localhost:6379) |
| `NATS_URL` | all Python services | NATS JetStream connection (default: nats://nats:4222) |

### Service-Specific

| Variable | Service | Description |
|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | payment | Stripe API key (empty → MockStripeClient) |
| `STRIPE_WEBHOOK_SECRET` | payment | Stripe webhook signing secret |
| `GEMINI_API_KEY` | ai, embedding-orchestrator | Google Gemini API key (empty → MockLLMProvider) |
| `GEMINI_MODEL` | ai | Model name (default: gemini-2.0-flash-lite) |
| `RESEND_API_KEY` | notification | Resend email API key (empty → StubEmailClient) |
| `CORS_ORIGINS` | api-gateway | Allowed origins (comma-separated) |
| `LOG_LEVEL` | all | Logging level (default: info) |
| `RAG_DB_URL` | seed script | RAG DB connection (postgresql://rag:rag@localhost:5439/rag) |

### Mock Mode

All external API dependencies are optional. Without API keys, services use mock providers:

| Provider | Env Var | Mock | Behavior |
|----------|---------|------|----------|
| Gemini LLM | `GEMINI_API_KEY` | `MockLLMProvider` | Returns realistic mock responses for all AI endpoints |
| Stripe | `STRIPE_SECRET_KEY` | `MockStripeClient` | Returns fake success data (cus_mock_xxx, sub_mock_xxx) |
| Resend | `RESEND_API_KEY` | `StubEmailClient` | Emails logged but not sent |
| Gemini Embeddings | `GEMINI_API_KEY` | `StubEmbeddingClient` | Random 768-dim vectors (search degraded) |

### Staging

Пример: `deploy/staging/.env.staging.example`

## Seed Data

### Demo B2B Organization — Acme Engineering

Создаётся автоматически при каждом запуске seed-скрипта (идемпотентно):

| Entity | Value |
|--------|-------|
| Admin user | `demo@acme.com` / `demo123` — Alex Chen, role=teacher |
| Organization | "Acme Engineering", slug=`acme` |
| Org members | 9 team members: sarah, mike, priya, james, yuki, carlos, emma, ali, lisa (all `@acme.com`) |
| Subscription | enterprise, active, 10/50 seats, $1000/mo |

Фиксированные UUID для предсказуемых ссылок:
- `DEMO_USER_ID` = `00000000-0000-4000-a000-000000000001`
- `DEMO_ORG_ID`  = `00000000-0000-4000-b000-000000000001`

### Demo RAG Documents — Acme Engineering Knowledge Base

Технические документы для RAG-демонстрации (5 документов, ~50 чанков, 47 концептов):

| Документ | Slug | Fixed UUID |
|----------|------|------------|
| Python Best Practices for Production Systems | `python_best_practices` | `00000000-0000-4001-c000-000000000001` |
| Rust Ownership, Borrowing, and Memory Safety | `rust_ownership` | `00000000-0000-4001-c000-000000000002` |
| TypeScript Patterns for Scalable Applications | `typescript_patterns` | `00000000-0000-4001-c000-000000000003` |
| System Design Fundamentals for Distributed Systems | `system_design` | `00000000-0000-4001-c000-000000000004` |
| API Design Guide: Building Developer-Friendly APIs | `api_design_guide` | `00000000-0000-4001-c000-000000000005` |

- Исходные файлы: `tools/seed/demo_documents/`
- Чанки: ~10 на документ по 200 слов, случайные нормализованные 768-мерные эмбеддинги
- Концепты: 47 штук (Python×10, Rust×10, TypeScript×9, System Design×9, API×9)
- Связи: 23 prerequisite-отношения (DAG: ownership→borrowing→lifetimes и т.д.)
- `RAG_DB_URL` env var обязателен для запуска seed-скрипта

### Demo Learning Data (for demo@acme.com)

| Entity | Count | Details |
|--------|-------|---------|
| Concepts | 47 | Python, Rust, TypeScript, System Design, API Design |
| Concept mastery (demo) | 47 | 10 mastered, 15 in-progress, 22 gaps |
| Concept mastery (team) | 9×47 | Per-member specializations |
| Missions | 16 | 15 completed + 1 pending, realistic blueprints |
| Flashcards | 25 | 10 due today, 15 future, FSRS state |
| Trust levels | 10 | Demo=4, team members=1-3 |
| Streak | 1 | current=7, longest=14 |
| XP events | 20 | ~2450 total XP |
| Badges | 3 | first_enrollment, streak_7, quiz_ace |
| Activity feed | 20 | Over 14 days |
| Notifications | 10 | 2 read + 8 unread (welcome, reminders, achievements) |
| Enrollments | 5 | 2 completed, 2 in-progress, 1 enrolled + lesson progress |

Team member UUIDs are deterministic (`uuid5(NAMESPACE_DNS, email)`) — consistent across identity-db and learning-db.

Тесты seed-скрипта: `cd tools/seed && uv run --package seed pytest tests/ -v`

## Development Commands

```bash
# Start all backends + databases
docker compose -f docker-compose.dev.yml up

# Seed test data (includes Acme Engineering demo org)
docker compose -f docker-compose.dev.yml --profile seed up seed

# Frontend
cd apps/buyer && pnpm dev     # port 3001
cd apps/seller && pnpm dev    # port 3002

# Tests
cd services/py/<name> && uv run --package <name> pytest tests/ -v
cd services/rs/<name> && cargo test && cargo clippy -- -D warnings

# Load testing (production compose)
docker compose -f docker-compose.prod.yml --profile loadtest up locust
# Locust UI: http://localhost:8089

# Monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
```

## Package Management

| Ecosystem | Tool | Config |
|-----------|------|--------|
| Python | uv | Root `pyproject.toml` with workspace members |
| JavaScript | pnpm | `pnpm-workspace.yaml` |
| Rust | cargo | Per-crate `Cargo.toml` |
| Monorepo | Turborepo | `turbo.json` (frontend builds) |
