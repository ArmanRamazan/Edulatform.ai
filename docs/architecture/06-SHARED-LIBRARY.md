# 06 — Shared Library (common)

> Последнее обновление: 2026-03-05
> Стадия: B2B Agentic Adaptive Learning Pivot

---

## Расположение

```
libs/py/common/
├── pyproject.toml       # hatchling build, installable package
├── tests/
│   └── test_logging.py  # 4 tests for configure_logging
└── common/
    ├── __init__.py
    ├── config.py         # BaseAppSettings
    ├── database.py       # create_pool(), update_pool_metrics()
    ├── errors.py         # AppError hierarchy + register_error_handlers()
    ├── health.py         # create_health_router() — liveness + readiness
    ├── logging.py        # configure_logging() — structlog JSON/console
    ├── rate_limit.py     # RateLimitConfig, RateLimiter, RateLimitMiddleware, rate_limit()
    ├── security.py       # create_access_token(), decode_token()
    └── sentry.py         # setup_sentry() — optional Sentry error tracking
```

**Установка:** `uv pip install /libs/common` или `common = { workspace = true }` в pyproject.toml сервиса.

---

## Использование

Все 6 активных сервисов (Identity, Payment, Notification, AI, Learning, RAG) используют common library. Dormant сервисы (Course, Enrollment) также зависят от common.

B2B pivot **не требует изменений** в common library. Все новые функции (organizations, missions, trust levels, RAG) реализуются на уровне сервисов, используя существующие модули common.

---

## Модули

### `common.config`

```python
class BaseAppSettings(BaseSettings):
    database_url: str
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 3600
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"
    rate_limit_per_minute: int = 100
```

Наследуется сервисами для добавления специфичных настроек. Все значения читаются из environment variables (pydantic-settings).

**Примеры наследования:**

```python
# Identity Service
class Settings(BaseAppSettings):
    refresh_token_ttl_days: int = 30

# AI Service (no DATABASE_URL)
class Settings(BaseSettings):  # Note: not BaseAppSettings
    redis_url: str = "redis://localhost:6379"
    jwt_secret: str = "change-me-in-production"
    gemini_api_key: str = ""
    learning_service_url: str = "http://localhost:8007"
    rag_service_url: str = "http://localhost:8008"

# RAG Service
class Settings(BaseAppSettings):
    gemini_api_key: str = ""
    github_token: str = ""
    embedding_model: str = "text-embedding-004"
    chunk_size: int = 500
    chunk_overlap: int = 50
```

---

### `common.database`

```python
async def create_pool(dsn: str, min_size: int = 5, max_size: int = 20) -> asyncpg.Pool
def update_pool_metrics(pool: asyncpg.Pool, service_name: str) -> None
```

- `create_pool()` — создаёт asyncpg connection pool с настраиваемым размером
- `update_pool_metrics()` — обновляет Prometheus gauges (pool size, free connections)

Используется всеми сервисами с БД: Identity, Payment, Notification, Learning, RAG. AI Service не использует (stateless).

---

### `common.errors`

```python
class AppError(Exception):
    message: str
    status_code: int = 400

class NotFoundError(AppError):     # 404
class ForbiddenError(AppError):    # 403
class ConflictError(AppError):     # 409

def register_error_handlers(app: FastAPI) -> None
```

`register_error_handlers()` добавляет exception handler для `AppError`, который возвращает `{"detail": error.message}` с соответствующим HTTP status code.

`ForbiddenError` активно используется для:
- Role-based access control (`role != admin`)
- Organization membership checks (NEW)
- Trust Level authorization (NEW)

---

### `common.security`

```python
def create_access_token(
    user_id: str,
    secret: str,
    algorithm: str = "HS256",
    ttl_seconds: int = 3600,
    extra_claims: dict | None = None,
) -> str

def decode_token(token: str, secret: str, algorithm: str = "HS256") -> dict
```

- `create_access_token()` — создаёт JWT с `sub`, `iat`, `exp` + optional extra_claims
- `decode_token()` — декодирует и валидирует JWT (проверяет expiration)

Extra claims используемые в B2B pivot:

```python
extra_claims = {
    "role": "student",
    "is_verified": False,
    "email_verified": True,
    "organization_id": "uuid-string"  # NEW: active organization context
}
```

---

### `common.logging`

```python
def configure_logging(service_name: str, log_level: str = "INFO") -> None
```

- Настраивает structlog + stdlib logging для structured JSON logging
- `ENVIRONMENT=production` — JSON renderer на stdout (для log aggregation)
- `ENVIRONMENT=development` — цветной ConsoleRenderer на stderr (для разработки)
- Добавляет `service` field во все log events через `bind_contextvars`
- Процессоры: `add_log_level`, `TimeStamper(iso)`, `format_exc_info`, `merge_contextvars`
- Подавляет шумные логгеры: uvicorn, httpcore, httpx
- Вызывается один раз в `lifespan()` каждого сервиса

**Использование в сервисах:**
```python
import structlog
from common.logging import configure_logging

# В lifespan:
configure_logging(service_name="rag")  # NEW service
logger = structlog.get_logger()
logger.info("service_started", port=8008)
```

---

### `common.health`

```python
def create_health_router(
    pool_getter: Callable[[], asyncpg.Pool | None],
    redis_getter: Callable[[], Redis | None] | None = None,
) -> APIRouter
```

Фабрика, возвращающая `APIRouter` с двумя endpoints:
- `GET /health/live` — всегда `{"status": "ok"}`, 200 (liveness probe)
- `GET /health/ready` — проверяет `pool.fetchval("SELECT 1")` и опционально `redis.ping()`. 200 если ок, 503 `{"status": "degraded"}` если нет (readiness probe)

RAG Service использует эту же фабрику — pgvector pool проверяется через стандартный `SELECT 1`.

---

### `common.rate_limit`

```python
@dataclass(frozen=True)
class RateLimitConfig:
    max_requests: int
    window_seconds: int
    key_type: str = "ip"              # "ip" | "user" | "ip_and_user"
    exclude_roles: tuple[str, ...] = ()  # e.g. ("admin",) to bypass limits
    dynamic_limit: Callable[[dict], int] | None = None  # returns 0 for unlimited

class RateLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None
    async def check(self, key: str) -> bool  # True if under limit

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_getter, limit: int, window: int) -> None

def rate_limit(
    config: RateLimitConfig,
    *,
    redis_getter: Callable | None = None,
    jwt_secret: str | None = None,
) -> Callable  # FastAPI Depends() factory
```

- `RateLimitConfig` — frozen dataclass for per-route rate limit configuration
- `RateLimiter` — sliding window counter через Redis INCR + EXPIRE
- `RateLimitMiddleware` — ASGI middleware, per-IP, 429 с `Retry-After` header
- `rate_limit()` — FastAPI dependency factory with dynamic limits, role exclusions, graceful degradation

---

### `common.sentry`

```python
def setup_sentry(dsn: str | None, service_name: str, environment: str = "production") -> None
```

- Optional Sentry error tracking integration via `sentry-sdk[fastapi]`
- If `dsn` is `None` or empty string — no-op, zero overhead
- If `dsn` is set — calls `sentry_sdk.init()` with FastAPI integration
- `send_default_pii=False` — never sends PII automatically
- `_before_send` filter strips sensitive headers (`Authorization`, `Cookie`) and PII fields
- Low sampling: `traces_sample_rate=0.1`, `profiles_sample_rate=0.1`
- Вызывается один раз в `lifespan()` каждого сервиса

---

## Правило выноса в common

Код выносится в `libs/py/common/` только когда используется в **2+ сервисах**. Все 7 модулей используются во всех активных сервисах. B2B pivot не добавляет новых модулей в common — новая функциональность (org checks, trust level checks) реализуется на уровне отдельных сервисов, а не в shared library (YAGNI — пока используется в 1 месте).
