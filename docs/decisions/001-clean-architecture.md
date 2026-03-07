# ADR-001: Clean Architecture for Python Services

**Status:** Accepted
**Date:** 2025-12-01
**Decision makers:** Core team

## Context
With 8 Python microservices, we need a consistent internal structure that:
- Keeps business logic testable without infrastructure
- Makes it easy for AI agents to understand and modify code
- Prevents coupling between layers

## Decision
All Python services follow Clean Architecture with strict dependency direction:

```
routes → services → domain ← repositories
```

- **domain/** — Pure Python entities (frozen dataclasses). No framework imports.
- **services/** — Use cases, orchestration. No HTTP concepts.
- **routes/** — HTTP handlers. No business logic, no direct repo access.
- **repositories/** — Data access. ABC interface + asyncpg implementation.

## Consequences
**Positive:**
- Business logic is framework-independent and easily testable
- AI agents can work on one layer without understanding others
- Repository swap (e.g., asyncpg → SQLAlchemy) doesn't affect services
- Consistent structure across 8 services reduces cognitive load

**Negative:**
- More boilerplate per feature (entity + repo + service + route)
- Simple CRUD requires touching 4 files minimum
- New developers need to learn the pattern

## Alternatives considered
1. **Fat routes** (FastAPI + SQLAlchemy ORM) — faster to write, harder to test, no separation
2. **Hexagonal architecture** — similar benefits, more abstract, harder for AI agents to follow
3. **Django-style MVT** — too opinionated, poor async support
