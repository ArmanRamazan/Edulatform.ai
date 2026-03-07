#!/usr/bin/env bash
# Run independent sprints in parallel, then sequential finishers.
#
# Wave 1 (parallel): sprint-32, sprint-35
# Wave 2 (sequential): sprint-36 (depends on wave 1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_DIR=".logs"
mkdir -p "$LOG_DIR"

# Check deps
python3 -c "import yaml" 2>/dev/null || { echo "ERROR: pyyaml missing"; exit 1; }
command -v claude &>/dev/null || { echo "ERROR: claude CLI not found"; exit 1; }

# ---------------------------------------------------------------
# Wave 1: Independent sprints (parallel)
# ---------------------------------------------------------------
echo ""
echo "================================================================"
echo "  WAVE 1: Parallel sprints (32, 35)"
echo "  Each sprint runs with isolated state via --instance"
echo "================================================================"
echo ""

PIDS=()
NAMES=()
LOGS=()

run_sprint() {
    local yaml="$1"
    local instance="$2"
    local log_file="$LOG_DIR/parallel-${instance}.log"

    # Reset instance state
    python3 main.py --reset --instance "$instance" > /dev/null 2>&1 || true

    echo "  [START] $instance -> $log_file"
    python3 main.py "$yaml" --instance "$instance" > "$log_file" 2>&1 &
    PIDS+=($!)
    NAMES+=("$instance")
    LOGS+=("$log_file")
}

run_sprint tasks/sprint-32-onboarding.yaml s32
run_sprint tasks/sprint-35-seed-data.yaml s35

echo ""
echo "  Waiting for ${#PIDS[@]} sprints..."
echo "  Monitor: tail -f $LOG_DIR/parallel-s*.log"
echo ""

# Wait and collect results
WAVE1_PASSED=0
WAVE1_FAILED=0

for i in "${!PIDS[@]}"; do
    pid="${PIDS[$i]}"
    name="${NAMES[$i]}"
    logf="${LOGS[$i]}"

    if wait "$pid"; then
        echo "  [PASSED] $name"
        ((WAVE1_PASSED++))
    else
        echo "  [FAILED] $name — see $logf"
        ((WAVE1_FAILED++))
    fi
done

echo ""
echo "  Wave 1: $WAVE1_PASSED passed, $WAVE1_FAILED failed"

if [ "$WAVE1_FAILED" -gt 0 ]; then
    echo ""
    echo "  Some sprints failed. Continue to Wave 2? (y/N)"
    read -r ans
    if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then
        echo "  Aborted."
        exit 1
    fi
fi

# ---------------------------------------------------------------
# Wave 2: Polish sprint (sequential, depends on wave 1)
# ---------------------------------------------------------------
echo ""
echo "================================================================"
echo "  WAVE 2: Sprint 36 (polish + integration)"
echo "================================================================"
echo ""

python3 main.py --reset --instance s36 > /dev/null 2>&1 || true

if python3 main.py tasks/sprint-36-polish.yaml --instance s36; then
    echo "  [PASSED] sprint-36"
else
    echo "  [FAILED] sprint-36"
    exit 1
fi

echo ""
echo "================================================================"
echo "  ALL DONE: $((WAVE1_PASSED + 1)) passed, $WAVE1_FAILED failed"
echo "================================================================"
