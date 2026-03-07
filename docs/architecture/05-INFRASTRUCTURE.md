# 05 — Infrastructure

> Последнее обновление: 2026-03-07

## Docker Compose

Три конфигурации:

| Config | Command | Purpose |
|--------|---------|---------|
| `docker-compose.dev.yml` | `docker compose -f docker-compose.dev.yml up` | Hot reload, debug ports, single-worker |
| `docker-compose.prod.yml` | `docker compose -f docker-compose.prod.yml up -d` | 4-worker uvicorn, monitoring, health checks |
| `docker-compose.staging.yml` | `docker compose -f docker-compose.staging.yml up -d` | Pre-built images, staging DB ports |

## Databases

PostgreSQL 16-alpine. Каждый сервис — своя БД:

| Service | DB Name | Dev Port | Staging Port |
|---------|---------|----------|-------------|
| identity | identity | 5433 | 5443 |
| course | course | 5434 | 5444 |
| enrollment | enrollment | 5435 | 5445 |
| payment | payment | 5436 | 5446 |
| notification | notification | 5437 | 5447 |
| learning | learning | 5438 | 5448 |
| rag | rag | 5439 | — |

**Redis 7-alpine** на порту 6379 — кэш и rate limiting.

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
| `deploy/scripts/backup-all-dbs.sh` | Параллельный pg_dump всех 6 БД → `deploy/backups/` |
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

### Service-Specific

| Variable | Service | Description |
|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | payment | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | payment | Stripe webhook signing secret |
| `GEMINI_API_KEY` | ai | Google Gemini API key |
| `GEMINI_MODEL` | ai | Model name (default: gemini-2.0-flash-lite) |
| `CORS_ORIGINS` | api-gateway | Allowed origins (comma-separated) |
| `LOG_LEVEL` | all | Logging level (default: info) |

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
