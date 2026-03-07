---
name: code-review
description: Review code changes against CLAUDE.md quality standards
---

# Code Review Checklist

## Trigger
Use when reviewing any code change before commit.

## Steps

### 1. Architecture compliance
- [ ] Clean Architecture respected: routes -> services -> domain <- repositories
- [ ] domain/ has NO imports from routes/, services/, repositories/, or frameworks
- [ ] routes/ does NOT call repositories directly
- [ ] services/ does NOT return HTTP codes or Response objects

### 2. Security
- [ ] SQL: parameterized queries only ($1, $2). No string concatenation
- [ ] Passwords: bcrypt/argon2 only. Never plaintext
- [ ] PII: masked in logs. No email/phone/card in log output
- [ ] Secrets: env vars only. Nothing hardcoded
- [ ] Input validation: pydantic in routes/ before passing to services/

### 3. Test quality
- [ ] Tests exist for new code (TDD: written first)
- [ ] Tests verify behavior, not implementation (no test tautologies)
- [ ] Tests are independent (no shared state, no order dependency)
- [ ] All tests pass: `uv run --package <name> pytest tests/ -v`

### 4. YAGNI
- [ ] No code "for the future"
- [ ] No unused files, classes, or functions
- [ ] No premature abstractions (3 similar lines > abstraction)
- [ ] No wrapper functions for single use

### 5. Code patterns
- [ ] Type hints on all public functions
- [ ] Domain entities: `dataclass(frozen=True)` or pydantic BaseModel
- [ ] Repository: `_COLUMNS`, `_to_entity()`, `_ALLOWED_UPDATE_COLUMNS`
- [ ] Service: owner check, role check, NotFoundError
- [ ] Named exports only. No default exports

### 6. Documentation
- [ ] CLAUDE.md updated if architecture changed
- [ ] STRUCTURE.md updated if new files/services
- [ ] docs/architecture/* updated if relevant
