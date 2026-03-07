#!/usr/bin/env bash
# Called by Claude Code hook after code edits
# Detects which Python services have uncommitted changes and reminds about testing
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo '.')"
changed_services=()

for svc in identity course enrollment payment notification ai learning rag; do
    if git diff --name-only HEAD 2>/dev/null | grep -q "services/py/$svc/"; then
        changed_services+=("$svc")
    fi
done

if [ ${#changed_services[@]} -gt 0 ]; then
    echo "CHANGED_SERVICES: ${changed_services[*]}"
    echo "Run tests before committing:"
    for svc in "${changed_services[@]}"; do
        echo "  cd services/py/$svc && uv run --package $svc pytest tests/ -v"
    done
fi
