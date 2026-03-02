#!/usr/bin/env bash
# EduPlatform Orchestrator v2 — launcher with process group management.
#
# Ensures all child processes (including claude CLI) are killed when:
#   - Ctrl+C is pressed
#   - Terminal is closed (SIGHUP)
#   - Script is killed (SIGTERM)
#
# Usage:
#   ./run.sh tasks/phase-2.5.yaml              # run task file
#   ./run.sh tasks/phase-*.yaml                # run multiple files
#   ./run.sh tasks/phase-2.5.yaml --dry-run    # preview
#   ./run.sh --resume                          # continue from state
#   ./run.sh --status                          # show progress
#   ./run.sh --reset                           # clear state
#   ./run.sh --is-running                      # check if running
#
# Stop gracefully:
#   Ctrl+C                              saves state, resumable
#   close terminal                      SIGHUP propagates, saves state
#   touch tools/orchestrator/.stop      from another terminal

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PID_FILE="$SCRIPT_DIR/.pid"

cd "$ROOT"

# Cleanup function — kill entire process group on exit
cleanup() {
    local exit_code=$?
    # Remove PID file
    rm -f "$PID_FILE"
    # Kill all processes in our process group (except ourselves)
    trap - SIGINT SIGTERM SIGHUP EXIT
    kill -- -$$ 2>/dev/null || true
    exit $exit_code
}

# Trap all termination signals
trap cleanup SIGINT SIGTERM SIGHUP EXIT

echo ""
echo "  +==========================================+"
echo "  |  EduPlatform Orchestrator v2             |"
echo "  |  Stop: Ctrl+C or close terminal          |"
echo "  +==========================================+"
echo ""

# Run orchestrator — exec replaces shell, inheriting signal handlers
# Python receives signals directly
exec uv run --package orchestrator python -u "$SCRIPT_DIR/orchestrator.py" "$@"
