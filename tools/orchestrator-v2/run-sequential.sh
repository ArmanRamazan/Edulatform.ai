#!/usr/bin/env bash
# Sequential sprint runner — one sprint at a time, no parallelism.
# Usage: cd tools/orchestrator-v2 && ./run-sequential.sh

set -euo pipefail
cd "$(dirname "$0")"

SPRINTS=(
  tasks/sprint-36-polish.yaml
  tasks/sprint-32-onboarding.yaml
  tasks/sprint-35-seed-data.yaml
  tasks/sprint-37-demo-ready.yaml
)

echo "============================================================"
echo "  SEQUENTIAL SPRINT RUNNER"
echo "  Sprints: ${#SPRINTS[@]}"
echo "  Order: ${SPRINTS[*]}"
echo "============================================================"

PASSED=0
FAILED=0

for sprint in "${SPRINTS[@]}"; do
  echo ""
  echo "============================================================"
  echo "  STARTING: $sprint"
  echo "  $(date)"
  echo "============================================================"

  # Reset state before each sprint
  python3 main.py --reset 2>/dev/null || true

  if python3 main.py "$sprint"; then
    echo "  V $sprint — PASSED"
    PASSED=$((PASSED + 1))
  else
    echo "  X $sprint — FAILED"
    FAILED=$((FAILED + 1))
  fi

  echo "  Finished: $(date)"
done

echo ""
echo "============================================================"
echo "  ALL DONE: $PASSED passed, $FAILED failed"
echo "============================================================"
