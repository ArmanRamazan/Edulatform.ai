---
name: migration-safety
description: Database migration safety checklist
---

# Migration Safety Checklist

## Trigger
Use when creating or reviewing any SQL migration file.

## Rules

### Idempotent
- All statements use `IF NOT EXISTS` / `IF EXISTS`
- Running migration twice produces same result
- Forward-only: no DOWN migrations

### No locks
- No `ALTER TABLE ... ADD COLUMN ... NOT NULL` without DEFAULT
- No `CREATE INDEX` without `CONCURRENTLY`
- No `LOCK TABLE`
- No long-running UPDATE in migration (use backfill script)

### Data safety
- Never DROP COLUMN in production migration
- Deprecate first (rename to _deprecated), drop in next release
- Never change column type directly -- add new column, migrate data, drop old

### Naming
- File: `migrations/XXX_<description>.sql` (sequential number)
- Tables: snake_case, plural (users, courses, enrollments)
- Columns: snake_case, singular
- Indexes: `idx_<table>_<columns>`
- Constraints: `uq_<table>_<columns>`, `fk_<table>_<ref>`

### Verify
```bash
# Check migration syntax
cd services/py/<name> && uv run --package <name> pytest tests/ -v
# Ensure tests still pass with new schema
```

### Template
```sql
-- Migration: XXX -- <description>
-- Service: <name>
-- Date: YYYY-MM-DD

CREATE TABLE IF NOT EXISTS <table> (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- ... columns
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_<table>_<column>
    ON <table> (<column>);
```
