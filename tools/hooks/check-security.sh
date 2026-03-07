#!/usr/bin/env bash
# Check for security anti-patterns in changed files
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"
issues=0

for f in $(git diff --name-only HEAD 2>/dev/null | grep -E "\.(py|ts|tsx)$"); do
    if [ -f "$ROOT/$f" ]; then
        # SQL injection: string formatting in SQL
        if grep -nE "f\"(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)" "$ROOT/$f" 2>/dev/null; then
            echo "SECURITY: $f — possible SQL injection (f-string in SQL)"
            issues=$((issues + 1))
        fi

        # Hardcoded secrets
        if grep -nE "(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}" "$ROOT/$f" 2>/dev/null; then
            echo "SECURITY: $f — possible hardcoded secret"
            issues=$((issues + 1))
        fi
    fi
done

if [ $issues -gt 0 ]; then
    echo "Found $issues potential security issues!"
    exit 1
fi
