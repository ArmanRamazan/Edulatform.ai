#!/usr/bin/env bash
# Run multiple sprints sequentially, stop on first failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

SPRINTS=(
    tasks/sprint-32-onboarding.yaml
    tasks/sprint-33-knowledge-graph.yaml
    tasks/sprint-34-realtime.yaml
    tasks/sprint-35-seed-data.yaml
    tasks/sprint-36-polish.yaml
)

PASSED=0
FAILED=0

for sprint in "${SPRINTS[@]}"; do
    echo ""
    echo "================================================================"
    echo "  STARTING: $sprint"
    echo "================================================================"
    echo ""

    ./run.sh --reset 2>/dev/null || true

    if ./run.sh "$sprint"; then
        echo "  >> PASSED: $sprint"
        ((PASSED++))
    else
        echo "  >> FAILED: $sprint"
        ((FAILED++))
        echo "  Stopping — fix failures before continuing."
        break
    fi
done

echo ""
echo "================================================================"
echo "  RESULTS: $PASSED passed, $FAILED failed"
echo "================================================================"
