# Common Library

Shared Python utilities used by all 8 Python services.

## Public API (from __init__.py)

- `BaseAppSettings` — pydantic BaseSettings for service config
- `create_pool` — asyncpg pool creation
- `AppError(400)`, `NotFoundError(404)`, `ConflictError(409)` — error hierarchy
- `register_error_handlers` — FastAPI exception handlers
- `create_health_router` — health check endpoints (liveness + readiness)
- `configure_logging` — structlog setup
- `create_access_token`, `decode_token` — JWT utilities

## Additional modules (not in __init__)

- `errors.py` — also has `ForbiddenError(403)`
- `rate_limit.py` — `RateLimitMiddleware` (Redis-backed)
- `sentry.py` — `setup_sentry()` integration
- `database.py` — also has `update_pool_metrics()`

## Rules

- Only add code here if used by 3+ services (YAGNI)
- Installable package (hatchling build system)
- Services reference via `common = { workspace = true }` in pyproject.toml
- `[tool.hatch.build.targets.wheel] packages = ["common"]`
- No dedicated tests — tested indirectly through service tests

## Patterns used by all services

- Lifespan: `create_pool()` -> repos -> services -> global getters
- Error handling: `register_error_handlers(app)` in every service
- Health: `create_health_router(pool_getter, redis_getter)` (redis optional)
- Rate limiting: `RateLimitMiddleware` with Redis getter
- Metrics: `update_pool_metrics(pool, service_name)` middleware
