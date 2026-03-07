#!/usr/bin/env bash
# Check for Clean Architecture violations in changed files
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"
violations=0

# Check domain/ doesn't import from routes/, services/, repositories/
for f in $(git diff --name-only HEAD 2>/dev/null | grep "domain/"); do
    if [ -f "$ROOT/$f" ]; then
        if grep -qE "from app\.(routes|services|repositories)" "$ROOT/$f" 2>/dev/null; then
            echo "VIOLATION: $f imports from wrong layer (domain must not import routes/services/repositories)"
            violations=$((violations + 1))
        fi
        if grep -qE "from (fastapi|starlette|asyncpg)" "$ROOT/$f" 2>/dev/null; then
            echo "VIOLATION: $f imports framework in domain layer"
            violations=$((violations + 1))
        fi
    fi
done

# Check routes/ doesn't import repositories directly
for f in $(git diff --name-only HEAD 2>/dev/null | grep "routes/"); do
    if [ -f "$ROOT/$f" ]; then
        if grep -qE "from app\.repositories" "$ROOT/$f" 2>/dev/null; then
            echo "VIOLATION: $f (route) imports repository directly"
            violations=$((violations + 1))
        fi
    fi
done

if [ $violations -gt 0 ]; then
    echo "Found $violations Clean Architecture violations!"
    exit 1
fi
