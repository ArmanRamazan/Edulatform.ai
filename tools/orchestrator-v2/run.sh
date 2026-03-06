#!/usr/bin/env bash
# Orchestrator v2 — Agile Sprint Pipeline launcher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found" >&2
    exit 1
fi

# Check PyYAML
python3 -c "import yaml" 2>/dev/null || {
    echo "ERROR: PyYAML not found. Install: pip install pyyaml" >&2
    exit 1
}

# Check Claude CLI
if ! command -v claude &>/dev/null; then
    echo "ERROR: claude CLI not found" >&2
    exit 1
fi

cd "$SCRIPT_DIR"
exec python3 main.py "$@"
