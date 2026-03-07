---
name: new-endpoint
description: Scaffold a new API endpoint following Clean Architecture patterns
---

# New Endpoint Workflow

## Trigger
Use when adding a new API endpoint to any Python service.

## Before starting
1. Read existing code in the target service to match style exactly
2. Read `tests/conftest.py` for fixture patterns
3. Read `app/main.py` for wiring pattern

## Steps (in order)

### 1. Domain entity (if new)
File: `app/domain/<entity>.py`
```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

@dataclass(frozen=True)
class <Entity>:
    id: UUID
    # ... fields
    created_at: datetime
```

### 2. Repository interface + implementation
File: `app/repositories/<entity>_repository.py`
```python
from abc import ABC, abstractmethod

class <Entity>Repository(ABC):
    @abstractmethod
    async def create(self, ...) -> <Entity>: ...
    @abstractmethod
    async def get_by_id(self, id: UUID) -> <Entity> | None: ...

class Pg<Entity>Repository(<Entity>Repository):
    _COLUMNS = "id, ..., created_at"
    _ALLOWED_UPDATE_COLUMNS = frozenset({"field1", "field2"})

    @staticmethod
    def _to_entity(row) -> <Entity>:
        return <Entity>(**dict(row))

    async def create(self, ...) -> <Entity>:
        row = await self._pool.fetchrow(
            f"INSERT INTO <table> ({self._COLUMNS}) VALUES ($1, ...) RETURNING {self._COLUMNS}",
            ...
        )
        return self._to_entity(row)
```

### 3. Service (business logic)
File: `app/services/<entity>_service.py`
- Constructor takes repository (abstract, not concrete)
- Owner/role checks: `if not authorized: raise ForbiddenError`
- Not found: `if not entity: raise NotFoundError`
- No HTTP concepts (no status codes, no Request/Response)

### 4. Route (HTTP handler)
File: `app/routes/<entity>_routes.py`
- Parse request (pydantic validation)
- Call service
- Format response
- No business logic

### 5. Wire in main.py
- Add repository creation in lifespan
- Add service creation
- Add router include

### 6. Migration (if new table)
File: `migrations/XXX_<description>.sql`
- `CREATE TABLE IF NOT EXISTS`
- Forward-only, idempotent
- No exclusive locks

### 7. Tests (TDD -- should be written FIRST)
- Unit tests: AsyncMock repos, test service logic
- Integration tests: real DB via conftest fixtures (if applicable)

### 8. Verify
```bash
cd services/py/<name> && uv run --package <name> pytest tests/ -v
```
