#!/usr/bin/env bash
# EduPlatform Orchestrator — launcher script
#
# Usage:
#   ./run.sh                        # run all remaining phases
#   ./run.sh --phase 2.4            # run specific phase
#   ./run.sh --phase 2.4 --dry-run  # preview tasks
#   ./run.sh --resume               # resume after pause
#   ./run.sh --status               # show progress
#
# Stop gracefully:
#   Ctrl+C                          # saves state, resumable
#   touch tools/orchestrator/.stop  # from another terminal

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$ROOT"

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║  EduPlatform Orchestrator                ║"
echo "  ║  Stop: Ctrl+C or touch .stop             ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# Run the orchestrator, passing all arguments through
exec uv run --package orchestrator python "$SCRIPT_DIR/orchestrator.py" "$@"
