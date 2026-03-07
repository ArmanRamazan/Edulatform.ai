# ADR-002: Database Per Service

**Status:** Accepted
**Date:** 2025-12-01
**Decision makers:** Core team

## Context
Microservices need data isolation. Shared database creates coupling, schema conflicts, and deployment dependencies.

## Decision
Each Python service owns its own PostgreSQL database on a dedicated port:

| Service | DB Port |
|---------|---------|
| identity | 5433 |
| course | 5434 |
| enrollment | 5435 |
| payment | 5436 |
| notification | 5437 |
| learning | 5438 |
| rag | 5439 |

Rules:
- A service NEVER reads another service's database
- Cross-service data access is via API calls only
- Each service manages its own migrations

## Consequences
**Positive:**
- Independent deployments — schema changes don't block other services
- Clear data ownership — no ambiguity about who manages what
- Independent scaling — hot services get dedicated DB resources
- Easier testing — each service test suite has isolated DB

**Negative:**
- Cross-service queries require API calls (higher latency)
- Data consistency is eventual, not transactional
- More infrastructure (7 DB instances in dev)
- Reporting/analytics requires data aggregation layer

## Alternatives considered
1. **Shared database, separate schemas** — simpler infra, but temptation to cross-query
2. **Shared database, shared schema** — simplest, but creates monolithic coupling
