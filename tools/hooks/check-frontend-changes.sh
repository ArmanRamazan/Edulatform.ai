#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"

if git diff --name-only HEAD 2>/dev/null | grep -q "apps/buyer/"; then
    echo "BUYER_CHANGED: Run 'cd apps/buyer && pnpm build' before committing"
fi

if git diff --name-only HEAD 2>/dev/null | grep -q "apps/seller/"; then
    echo "SELLER_CHANGED: Run 'cd apps/seller && pnpm build' before committing"
fi
