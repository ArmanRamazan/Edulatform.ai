# 06 — Shared Libraries

> Последнее обновление: 2026-03-06

---

## libs/py/common (Python)

Общая библиотека для всех Python сервисов. Установлена как hatchling package, сервисы подключают через `workspace = true`.

### common/errors.py

```python
class AppError(Exception):
    """Base error. Status code 400."""
    def __init__(self, message: str, status_code: int = 400): ...

class NotFoundError(AppError):
    """404 Not Found."""
    def __init__(self, message: str = "Not found"): ...

class ForbiddenError(AppError):
    """403 Forbidden. Used for role-based access control."""
    def __init__(self, message: str = "Forbidden"): ...

class ConflictError(AppError):
    """409 Conflict. Used for UNIQUE constraint violations."""
    def __init__(self, message: str = "Conflict"): ...
```

Паттерн: repositories ловят `asyncpg.UniqueViolationError` и бросают `ConflictError`. Services никогда не импортируют asyncpg.

### common/security.py

```python
def create_access_token(
    user_id: str,
    secret: str,
    extra_claims: dict | None = None,
    expires_seconds: int = 3600,
) -> str:
    """Create JWT HS256 token.

    extra_claims: role, is_verified, email_verified,
                  organization_id, subscription_tier
    """

def decode_token(token: str, secret: str) -> dict:
    """Decode and validate JWT. Raises AppError on invalid/expired."""
```

### common/database.py

```python
async def create_pool(database_url: str) -> asyncpg.Pool:
    """Create async PostgreSQL connection pool."""

async def run_migrations(pool: asyncpg.Pool, migrations_dir: str) -> None:
    """Run forward-only idempotent SQL migrations from directory."""
```

### common/config.py

```python
class BaseAppSettings(BaseSettings):
    """Pydantic BaseSettings for service configuration.

    Reads from environment variables:
    - DATABASE_URL
    - JWT_SECRET
    - REDIS_URL
    - LOG_LEVEL
    """
```

### common/logging.py

Structured JSON logging setup. Masks PII (email, phone) in log output.

---

## libs/rs/rag-chunker (Rust + PyO3)

Markdown-aware chunking crate, exposed to Python via PyO3 FFI.

### Cargo.toml

```toml
[package]
name = "rag-chunker"

[lib]
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.22", features = ["extension-module"] }
```

### API (Python)

```python
import rag_chunker

chunks = rag_chunker.chunk_markdown(
    text="# Header\n\nParagraph with code:\n```python\nprint('hello')\n```",
    max_tokens=512,
)

for chunk in chunks:
    chunk.content      # str — chunk text
    chunk.headings     # list[str] — parent headings context
    chunk.code_lang    # str | None — programming language if code block
    chunk.token_count  # int — approximate token count
```

### Features

- Markdown-aware splitting (respects headers, code blocks, lists)
- Metadata enrichment (parent headings propagated to chunks)
- Code language detection
- Token counting (approximate, whitespace-based)
- Python fallback в rag service если FFI недоступен

### Testing

```bash
cd libs/rs/rag-chunker && cargo test && cargo clippy -- -D warnings
```
