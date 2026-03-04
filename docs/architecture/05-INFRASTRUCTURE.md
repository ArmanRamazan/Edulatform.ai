# 05 — Infrastructure & Docker

> Последнее обновление: 2026-03-03
> Стадия: Phase 3.2 (Monetization backend — Stripe, subscriptions, earnings, payouts)

---

## Docker Compose — два режима

### Dev (`docker-compose.dev.yml`)

```bash
docker compose -f docker-compose.dev.yml up
```

- Hot reload через volume mounts (`app/`, `migrations/`, `common/`)
- Debug ports для БД доступны с хоста
- Без мониторинга (нет Prometheus/Grafana)
- `--reload` флаг для uvicorn
- Graceful shutdown: `--timeout-graceful-shutdown 10`

**Сервисы:**
| Container | Image / Build | Порт |
|-----------|--------------|------|
| identity-db | postgres:16-alpine | 5433 |
| course-db | postgres:16-alpine | 5434 |
| enrollment-db | postgres:16-alpine | 5435 |
| payment-db | postgres:16-alpine | 5436 |
| notification-db | postgres:16-alpine | 5437 |
| learning-db | postgres:16-alpine | 5438 |
| redis | redis:7-alpine | 6379 |
| identity | Dockerfile build | 8001 |
| course | Dockerfile build | 8002 |
| enrollment | Dockerfile build | 8003 |
| payment | Dockerfile build | 8004 |
| notification | Dockerfile build | 8005 |
| ai | Dockerfile build | 8006 |
| learning | Dockerfile build | 8007 |
| seed (profile) | Dockerfile build | — |

### Staging (`docker-compose.staging.yml`)

```bash
docker compose -f docker-compose.staging.yml up -d
# Seed demo data:
docker compose -f docker-compose.staging.yml --profile seed up seed
```

- Pre-built images from GHCR (`ghcr.io/{owner}/{service}:latest`)
- 2 uvicorn workers (lower resource usage than prod)
- No monitoring stack (no Prometheus/Grafana)
- Staging-specific DB ports (5443–5448), Redis on 6380
- Env vars via `deploy/staging/.env.staging` (env_file) + `ENVIRONMENT=staging`
- Seed profile for demo data on first run

**Сервисы:**
| Container | Image | Порт (host) |
|-----------|-------|-------------|
| identity-db | postgres:16-alpine | 5443 |
| course-db | postgres:16-alpine | 5444 |
| enrollment-db | postgres:16-alpine | 5445 |
| payment-db | postgres:16-alpine | 5446 |
| notification-db | postgres:16-alpine | 5447 |
| learning-db | postgres:16-alpine | 5448 |
| redis | redis:7-alpine | 6380 |
| identity | ghcr.io/{owner}/identity | 8001 |
| course | ghcr.io/{owner}/course | 8002 |
| enrollment | ghcr.io/{owner}/enrollment | 8003 |
| payment | ghcr.io/{owner}/payment | 8004 |
| notification | ghcr.io/{owner}/notification | 8005 |
| ai | ghcr.io/{owner}/ai | 8006 |
| learning | ghcr.io/{owner}/learning | 8007 |
| seed (profile) | ghcr.io/{owner}/seed | — |

### Prod (`docker-compose.prod.yml`)

```bash
docker compose -f docker-compose.prod.yml up -d
```

- Multi-worker uvicorn (4 workers)
- Prometheus + Grafana мониторинг
- Locust нагрузочное тестирование (profile)
- Без volume mounts (код запечён в image)
- Graceful shutdown: `--timeout-graceful-shutdown 25`, `stop_grace_period: 30s`
- CORS: настраивается через `ALLOWED_ORIGINS` env var
- Rate limiting: per-IP через Redis sliding window

**Дополнительные сервисы:**
| Container | Image | Порт |
|-----------|-------|------|
| prometheus | prom/prometheus | 9090 |
| grafana | grafana/grafana | 3000 |
| locust (profile) | Dockerfile build | 8089 |

---

## Dockerfiles

Все Python Dockerfiles используют одинаковый паттерн:

```dockerfile
FROM python:3.12-slim

# uv binary (direct download, не COPY --from т.к. WSL2 credential issues)
ADD https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-unknown-linux-gnu.tar.gz /tmp/uv.tar.gz
RUN tar -xzf /tmp/uv.tar.gz -C /tmp \
    && mv /tmp/uv-x86_64-unknown-linux-gnu/uv /bin/uv \
    && rm -rf /tmp/uv*

WORKDIR /app

# Shared library
COPY libs/py/common /libs/common

# Dependencies install (layer cache)
COPY services/py/<service>/pyproject.toml .
RUN uv venv /app/.venv \
    && uv pip install --python /app/.venv /libs/common \
    && uv pip install --python /app/.venv <dependencies>

ENV PATH="/app/.venv/bin:$PATH"

# Application code
COPY services/py/<service>/ .

EXPOSE <port>
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "<port>"]
```

**Файлы:**
- `deploy/docker/identity.Dockerfile`
- `deploy/docker/course.Dockerfile`
- `deploy/docker/enrollment.Dockerfile`
- `deploy/docker/payment.Dockerfile`
- `deploy/docker/notification.Dockerfile`
- `deploy/docker/learning.Dockerfile`
- `deploy/docker/seed.Dockerfile`
- `deploy/docker/locust.Dockerfile`

---

## Environment Variables

### Общие (все Python сервисы)

| Variable | Default | Описание |
|----------|---------|----------|
| `DATABASE_URL` | — (required) | PostgreSQL DSN |
| `REDIS_URL` | `redis://redis:6379` | Redis DSN (rate limiting, кэш) |
| `JWT_SECRET` | `change-me-in-production` | Shared JWT secret |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `JWT_TTL_SECONDS` | `3600` | Access token lifetime |
| `ALLOWED_ORIGINS` | `http://localhost:3000,http://localhost:3001` | CORS allowed origins (comma-separated) |
| `RATE_LIMIT_PER_MINUTE` | `100` | Global per-IP rate limit |
| `SENTRY_DSN` | `""` (empty) | Sentry DSN; empty = disabled |
| `ENVIRONMENT` | `production` | Environment name (production, staging, development) |

### Identity-specific

| Variable | Default | Описание |
|----------|---------|----------|
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Refresh token lifetime |

Endpoint-specific rate limits (Identity, не настраиваемые):
- `POST /login` — 10 req/min per IP
- `POST /register` — 5 req/min per IP

### Payment-specific

| Variable | Default | Описание |
|----------|---------|----------|
| `STRIPE_SECRET_KEY` | `""` (empty) | Stripe API secret key |
| `STRIPE_WEBHOOK_SECRET` | `""` (empty) | Stripe webhook signing secret |

### Notification-specific

| Variable | Default | Описание |
|----------|---------|----------|
| `RESEND_API_KEY` | `""` (empty) | Resend API key; empty = StubEmailClient (logs only) |
| `EMAIL_FROM_ADDRESS` | `noreply@eduplatform.ru` | Sender address for outgoing emails |
| `LEARNING_SERVICE_URL` | `http://localhost:8007/api/learning` | Learning service URL for smart reminders |

### Dev compose values

| Service | DATABASE_URL | JWT_SECRET |
|---------|-------------|------------|
| identity | `postgresql://identity:identity@identity-db:5432/identity` | `dev-secret-key` |
| course | `postgresql://course:course@course-db:5432/course` | `dev-secret-key` |
| enrollment | `postgresql://enrollment:enrollment@enrollment-db:5432/enrollment` | `dev-secret-key` |
| payment | `postgresql://payment:payment@payment-db:5432/payment` | `dev-secret-key` |
| notification | `postgresql://notification:notification@notification-db:5432/notification` | `dev-secret-key` |
| ai | — (stateless, Redis cache only) | `dev-secret-key` |
| learning | `postgresql://learning:learning@learning-db:5432/learning` | `dev-secret-key` |

### Seed-specific

| Variable | Value | Описание |
|----------|-------|----------|
| `IDENTITY_DB_URL` | `postgresql://identity:identity@identity-db:5432/identity` | Identity DB |
| `COURSE_DB_URL` | `postgresql://course:course@course-db:5432/course` | Course DB |
| `ENROLLMENT_DB_URL` | `postgresql://enrollment:enrollment@enrollment-db:5432/enrollment` | Enrollment DB |
| `PAYMENT_DB_URL` | `postgresql://payment:payment@payment-db:5432/payment` | Payment DB |
| `NOTIFICATION_DB_URL` | `postgresql://notification:notification@notification-db:5432/notification` | Notification DB |
| `LEARNING_DB_URL` | `postgresql://learning:learning@learning-db:5432/learning` | Learning DB |

---

## Seed Data

```bash
docker compose -f docker-compose.dev.yml --profile seed up seed
```

Скрипт `tools/seed/seed.py` генерирует:
- **1 admin** (`admin@eduplatform.com` / `password123`) — создаётся через INSERT перед bulk COPY
- **50,000 пользователей**: 80% students, 20% teachers (из них 70% verified)
- **100,000 курсов**: привязаны к verified teachers
- **~35,000 модулей**: 3-5 модулей на курс (первые 10K курсов)
- **~210,000 уроков**: 3-8 уроков на модуль (первые 10K курсов)
- **~100,000 отзывов**: рейтинг 1-5 (weighted: 40% пятёрок), обновляет avg_rating/review_count
- **200,000 записей (enrollments)**: 60% на бесплатные курсы, 40% на платные
- **50,000 оплат (payments)**: для платных курсов, status=completed
- **Learning data**: quizzes, concepts, flashcards, XP, badges, streaks, leaderboard, comments
- Пароль для всех: `password123` (bcrypt hash)

---

## Database Backup & Restore

Scripts in `deploy/scripts/`:

```bash
# Backup all 6 databases (compressed .sql.gz)
./deploy/scripts/backup-all-dbs.sh

# List existing backups
./deploy/scripts/list-backups.sh

# Restore a specific database (requires --confirm flag)
./deploy/scripts/restore-db.sh identity deploy/backups/identity-2026-03-03-120000.sql.gz --confirm
```

- Backups saved to `deploy/backups/` (gitignored)
- Uses `pg_dump` via `docker exec` on running containers
- Restore drops and recreates the target database
- Supported services: identity, course, enrollment, payment, notification, learning

---

## Monitoring (Prod only)

### Prometheus

Scrape config (`deploy/docker/prometheus/prometheus.yml`):
- `scrape_interval: 5s`
- Jobs: `identity` (`:8001`), `course` (`:8002`), `enrollment` (`:8003`), `payment` (`:8004`), `notification` (`:8005`), `ai` (`:8006`), `learning` (`:8007`)

Метрики автоматически экспортируются через `prometheus-fastapi-instrumentator`:
- `http_requests_total` — счётчик запросов
- `http_request_duration_seconds` — histogram latency
- `http_requests_in_progress` — gauge текущих запросов
- `http_response_size_bytes` — histogram размера ответов

### Grafana

- Datasource: Prometheus (auto-provisioned)
- Dashboard: `services.json` (auto-provisioned)
- Панели: Request Rate, Error Rate, P50/P95/P99 Latency, In-Progress, Response Size
- Refresh: 5s
- Default creds: admin/admin

---

## Load Testing (Prod only)

```bash
docker compose -f docker-compose.prod.yml --profile loadtest up locust
```

Locust UI: http://localhost:8089

**Сценарии** (`tools/locust/locustfile.py`):

| User Type | Weight | Действия |
|-----------|--------|----------|
| StudentUser | 7 | list_courses (5), view_course (3), view_curriculum (3), view_lesson (2), enroll_in_course (2), complete_lesson (1) |
| SearchUser | 2 | search_courses — ILIKE по random term |
| TeacherUser | 1 | get_me (2), create_course (1), list_my_courses (1) |

---

## Health Checks

### Infrastructure (Docker healthcheck)

| Container | Check | Interval | Timeout | Retries |
|-----------|-------|----------|---------|---------|
| identity-db | `pg_isready -U identity` | 5s | 3s | 5 |
| course-db | `pg_isready -U course` | 5s | 3s | 5 |
| enrollment-db | `pg_isready -U enrollment` | 5s | 3s | 5 |
| payment-db | `pg_isready -U payment` | 5s | 3s | 5 |
| notification-db | `pg_isready -U notification` | 5s | 3s | 5 |
| learning-db | `pg_isready -U learning` | 5s | 3s | 5 |
| redis | `redis-cli ping` | 5s | 3s | 5 |

Все сервисы запускаются после `service_healthy` condition на своих БД.

### Application-level (все 7 Python сервисов)

| Endpoint | Описание | Checks |
|----------|----------|--------|
| `GET /health/live` | Liveness probe — процесс жив | Всегда `{"status": "ok"}`, 200 |
| `GET /health/ready` | Readiness probe — зависимости доступны | PostgreSQL pool + Redis ping; 503 если недоступны |

Docker healthcheck в prod compose использует `/health/live` (python urllib, без curl).

Реализация: `libs/py/common/common/health.py` — фабрика `create_health_router(pool_getter, redis_getter=None)`.

---

## Graceful Shutdown

Uvicorn обрабатывает SIGTERM: перестаёт принимать новые соединения, ждёт завершения in-flight requests. Lifespan cleanup закрывает pool и redis.

| Режим | `--timeout-graceful-shutdown` | `stop_grace_period` |
|-------|-------------------------------|---------------------|
| Dev | 10s | — |
| Prod | 25s | 30s |

---

## Middleware Stack (все сервисы)

Порядок middleware (снаружи внутрь):

1. **CORS** (`CORSMiddleware`) — origins из `ALLOWED_ORIGINS`, credentials=true
2. **Rate Limiting** (`RateLimitMiddleware`) — per-IP sliding window через Redis
3. **Pool Metrics** — обновление Prometheus gauge (pool size/free)
4. **Prometheus Instrumentator** — HTTP request metrics

---

## Frontend (вне Docker)

Frontend-приложения запускаются отдельно через pnpm:

```bash
cd apps/buyer && pnpm dev   # :3001
cd apps/seller && pnpm dev  # :3002
```

**Buyer App** проксирует API через Next.js rewrites:
- `/api/identity/*` → `http://localhost:8001/*`
- `/api/course/*` → `http://localhost:8002/*`
- `/api/enrollment/*` → `http://localhost:8003/*`
- `/api/payment/*` → `http://localhost:8004/*`
- `/api/notification/*` → `http://localhost:8005/*`
- `/api/learning/*` → `http://localhost:8007/*`

**Seller App** проксирует API через Next.js rewrites:
- `/api/identity/*` → `http://localhost:8001/*`
- `/api/course/*` → `http://localhost:8002/*`
- `/api/payment/*` → `http://localhost:8004/*`
- `/api/notification/*` → `http://localhost:8005/*`
