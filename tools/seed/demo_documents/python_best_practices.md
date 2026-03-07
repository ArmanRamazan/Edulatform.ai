# Python Best Practices for Production Systems

## Introduction

Writing Python code that works in a demo is easy. Writing Python code that runs reliably at scale, is maintainable by a team of engineers over years, and handles failure gracefully is an entirely different discipline. This document covers the practical patterns, idioms, and conventions that separate production-grade Python from throwaway scripts.

## Type Hints and Static Analysis

Python's type hint system, introduced in PEP 484, is one of the most important tools available for large codebases. Type hints are not enforced at runtime by default, but they are invaluable for static analysis tools like mypy and pyright.

Annotate all public functions and methods:

```python
from typing import Optional
from uuid import UUID

def get_user_by_id(user_id: UUID, include_deleted: bool = False) -> Optional[dict]:
    ...
```

Use `from __future__ import annotations` at the top of modules where you use forward references or complex annotations. This makes all annotations strings at runtime, avoiding circular import issues and improving performance.

For collections, prefer the built-in generic forms available since Python 3.9: `list[str]`, `dict[str, int]`, `tuple[int, ...]` instead of `List`, `Dict`, `Tuple` from `typing`.

Use `TypeAlias` (Python 3.10+) or type aliases for complex types that appear in multiple places:

```python
from typing import TypeAlias

UserId: TypeAlias = UUID
OrgId: TypeAlias = UUID
```

Run mypy with `--strict` in CI. Address every warning. The initial investment pays dividends when refactoring because the type checker catches entire classes of bugs before they reach production.

## Async/Await Patterns

Python's asyncio model is cooperative: coroutines yield control voluntarily at `await` points. Understanding this is essential to writing correct async code.

Always `await` I/O operations. Never block the event loop with synchronous calls inside async functions. If you must call a blocking function, run it in a thread pool:

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=4)

async def read_large_file(path: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, Path(path).read_bytes)
```

Use `asyncio.gather()` for concurrent operations that do not depend on each other:

```python
async def fetch_user_dashboard(user_id: UUID) -> dict:
    profile, orders, notifications = await asyncio.gather(
        get_profile(user_id),
        get_recent_orders(user_id),
        get_unread_count(user_id),
    )
    return {"profile": profile, "orders": orders, "unread": notifications}
```

Be careful with `asyncio.gather()` error handling. By default, if one coroutine raises, others continue running. Use `return_exceptions=True` when you want to collect all results or errors and handle them together.

Avoid creating new event loops manually. In FastAPI and modern async frameworks, an event loop is managed for you. Use `asyncio.get_event_loop()` or `asyncio.get_running_loop()` only when you genuinely need a reference to the loop.

## Testing Patterns

Testing async Python code requires pytest-asyncio. Configure it with `asyncio_mode = "auto"` in `pyproject.toml` so every `async def test_*` function is automatically treated as an async test.

Use `AsyncMock` for mocking coroutines:

```python
from unittest.mock import AsyncMock, patch

async def test_user_service_returns_not_found_for_missing_user():
    repo = AsyncMock(spec=UserRepository)
    repo.get_by_id.return_value = None

    service = UserService(repo)
    result = await service.get_user(uuid4())

    assert result is None
    repo.get_by_id.assert_called_once()
```

Test behavior, not implementation. A test that only verifies a mock was called is not testing your code, it is testing that you can call a mock. Tests should assert the observable outcome of an operation.

Use `testcontainers` for integration tests that need a real database. Start a PostgreSQL container, run migrations, and execute queries against a real connection:

```python
from testcontainers.postgres import PostgresContainer

@pytest.fixture(scope="session")
async def pg_container():
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres.get_connection_url()
```

Separate unit tests (fast, no I/O, mock everything external) from integration tests (slower, real DB, test the full stack from service to SQL). Run unit tests on every commit, integration tests on every PR.

## Project Structure

A well-structured Python service follows Clean Architecture principles. The key constraint is that dependencies point inward: HTTP handlers call services, services call repositories and domain logic, domain has no outward dependencies.

```
services/py/my_service/
├── app/
│   ├── config.py          # Pydantic BaseSettings reading from env vars
│   ├── main.py            # FastAPI app, lifespan, dependency wiring
│   ├── domain/            # Pure Python: dataclasses, value objects, business rules
│   ├── services/          # Use cases: orchestrate domain + repositories
│   ├── repositories/      # Abstract interface (ABC) + asyncpg implementation
│   └── routes/            # FastAPI routers: parse request, call service, return response
├── tests/
│   ├── conftest.py        # Fixtures: DB pool, service instances, test data
│   └── test_*.py
└── migrations/
    └── 001_init.sql
```

Configuration must come from environment variables. Use Pydantic's `BaseSettings`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    debug: bool = False

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

settings = Settings()
```

## Decorators and Metaprogramming

Decorators are Python's primary mechanism for cross-cutting concerns: logging, caching, retries, authorization checks. A well-written decorator is transparent to the function it wraps.

Always use `functools.wraps` to preserve the original function's metadata:

```python
import functools
import logging

logger = logging.getLogger(__name__)

def log_calls(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info("Calling %s", func.__name__)
        result = await func(*args, **kwargs)
        logger.info("%s completed", func.__name__)
        return result
    return wrapper
```

## Generators and Context Managers

Generators are memory-efficient for processing large datasets. Instead of loading all records into memory, stream them:

```python
async def iter_all_users(pool) -> AsyncIterator[User]:
    async with pool.acquire() as conn:
        async for row in conn.cursor("SELECT * FROM users ORDER BY created_at"):
            yield User.from_row(row)
```

Context managers (`with` statement) guarantee cleanup even when exceptions occur. Implement the protocol with `__enter__`/`__exit__` or use `contextlib.contextmanager`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def transaction(pool):
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
```

## Error Handling

Establish a hierarchy of domain exceptions. Catch low-level exceptions at the boundary (repository layer) and convert them to domain exceptions that services and routes understand:

```python
class AppError(Exception):
    status_code: int = 500
    message: str = "Internal server error"

class NotFoundError(AppError):
    status_code = 404

class ConflictError(AppError):
    status_code = 409
```

In FastAPI, register an exception handler:

```python
@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message},
    )
```

Never swallow exceptions silently. At minimum, log them. In production, send them to your error tracking service (Sentry, Honeybadger). An exception you do not know about is a bug you can never fix.

## Logging

Use Python's standard `logging` module. Configure it once at application startup. Never use `print()` for operational output in production code.

Structure your logs as JSON in production so they are parseable by log aggregation systems:

```python
import logging
import json

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)
```

Add contextual fields to logs using `logging.LoggerAdapter` or `structlog`. Include `user_id`, `request_id`, and `org_id` in every log line within a request context.

## Virtual Environments and Dependency Management

Use `uv` for dependency management. It is orders of magnitude faster than pip and handles virtual environments automatically. Pin exact versions in lock files, use version ranges in `pyproject.toml`.

Never install packages into the system Python. Each project gets its own virtual environment. In production containers, install into `/app/.venv` and add it to `PATH`.

Keep `pyproject.toml` minimal. Only include direct dependencies. Let the lock file handle transitive dependencies. Audit your dependencies periodically and remove unused ones. Every dependency is a potential security vulnerability and a maintenance burden.
