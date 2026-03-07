---
name: deploy-checklist
description: Pre-deployment verification checklist
---

# Deploy Checklist

## Trigger
Use before any deployment or when preparing for release.

## Pre-deploy checks

### 1. All tests green
```bash
# Run all Python services
for svc in identity course enrollment payment notification ai learning rag; do
  echo "=== $svc ===" && cd services/py/$svc && uv run --package $svc pytest tests/ -v && cd ../../..
done

# Run Rust services
cd services/rs/api-gateway && cargo test && cargo clippy -- -D warnings && cd ../../..

# Run frontend builds
cd apps/buyer && pnpm build && cd ../..
cd apps/seller && pnpm build && cd ../..
```

### 2. Migrations
- [ ] All migrations are idempotent (IF NOT EXISTS)
- [ ] No locking operations (see migration-safety skill)
- [ ] Migration order matches dependency order

### 3. Environment
- [ ] All new env vars documented in docker-compose files
- [ ] No hardcoded secrets in code
- [ ] .env.example updated if new vars added

### 4. Docker
```bash
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d
# Verify all services healthy
docker compose -f docker-compose.dev.yml ps
```

### 5. Documentation
- [ ] README.md reflects current state
- [ ] STRUCTURE.md updated for new files
- [ ] docs/architecture/* current
- [ ] API reference updated for new endpoints

### 6. Performance
- [ ] No N+1 queries in new code
- [ ] Pagination on list endpoints
- [ ] Indexes on queried columns
