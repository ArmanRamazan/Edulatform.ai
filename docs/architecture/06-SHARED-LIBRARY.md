# 06 — Shared Library (common)

> Последнее обновление: 2026-02-25
> Стадия: Phase 2.3 (Knowledge Graph + Adaptive Path)

---

## Расположение

```
libs/py/common/
├── pyproject.toml       # hatchling build, installable package
└── common/
    ├── __init__.py
    ├── config.py         # BaseAppSettings
    ├── database.py       # create_pool(), update_pool_metrics()
    ├── errors.py         # AppError hierarchy + register_error_handlers()
    ├── health.py         # create_health_router() — liveness + readiness
    ├── rate_limit.py     # RateLimiter, RateLimitMiddleware
    └── security.py       # create_access_token(), decode_token()
```

**Установка:** `uv pip install /libs/common` или `common = { workspace = true }` в pyproject.toml сервиса.

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

---

### `common.database`

```python
async def create_pool(dsn: str, min_size: int = 5, max_size: int = 20) -> asyncpg.Pool
def update_pool_metrics(pool: asyncpg.Pool, service_name: str) -> None
```

- `create_pool()` — создаёт asyncpg connection pool с настраиваемым размером
- `update_pool_metrics()` — обновляет Prometheus gauges (pool size, free connections)

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

- `create_access_token()` — создаёт JWT с `sub`, `iat`, `exp` + optional extra_claims (role, is_verified)
- `decode_token()` — декодирует и валидирует JWT (проверяет expiration)

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

---

### `common.rate_limit`

```python
class RateLimiter:
    def __init__(self, redis: Redis, limit: int, window_seconds: int) -> None
    async def check(self, key: str) -> bool  # True if under limit

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, redis_getter, limit: int, window: int) -> None
```

- `RateLimiter` — sliding window counter через Redis INCR + EXPIRE
- `RateLimitMiddleware` — ASGI middleware, извлекает IP из `request.client.host`, при превышении возвращает `429 Too Many Requests` с `Retry-After` header
- Пропускает `/health/` и `/metrics` endpoints

---

## Использование в сервисах

```python
# services/py/identity/app/config.py
from common.config import BaseAppSettings

class Settings(BaseAppSettings):
    jwt_ttl_seconds: int = 3600   # переопределение

# services/py/course/app/config.py
from common.config import BaseAppSettings

class Settings(BaseAppSettings):
    pass                           # всё из базового класса
```

---

## Правило выноса в common

Код выносится в `libs/py/common/` только когда используется в **2+ сервисах**. Все 6 модулей используются во всех 7 сервисах (Identity, Course, Enrollment, Payment, Notification, AI, Learning).
