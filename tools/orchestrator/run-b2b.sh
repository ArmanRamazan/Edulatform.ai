#!/usr/bin/env bash
# B2B Knowledge Platform — full build pipeline.
#
# Launches sprints in dependency order, parallelizing independent sprints.
# Uses --multi-agent mode for wave-based parallel execution within each sprint.
#
# Usage:
#   ./run-b2b.sh                    # run remaining sprints (Phase 2-4)
#   ./run-b2b.sh --dry-run          # preview only
#   ./run-b2b.sh --phase 2          # run specific phase (2-4)
#   ./run-b2b.sh --resume           # resume from where it stopped
#
# Completed:
#   Phase 1: Sprint 19 + 21 (DONE — mission engine + dark knowledge foundation)
#
# Remaining:
#   Phase 2: Sprint 22 (knowledge platform UI)
#   Phase 3: Sprint 23 + 26 (parallel — Rust gateway + B2B admin)
#   Phase 4: Sprint 24 + 25 + 27 (Rust perf + MCP, depends on phase 3)
#
# Stop: Ctrl+C (saves state, resumable)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TASKS="$SCRIPT_DIR/tasks"

cd "$ROOT"

DRY_RUN=""
PHASE=""
RESUME=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN="--dry-run" ;;
        --phase)   shift; PHASE="$1" ;;
        --resume)  RESUME="--resume" ;;
        [2-4])     PHASE="$arg" ;;
    esac
done

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${BLUE}  ╔══════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}  ║  B2B Knowledge Platform — Build Pipeline    ║${NC}"
    echo -e "${BLUE}  ║  Mode: multi-agent (wave-based parallel)    ║${NC}"
    echo -e "${BLUE}  ║  Phase 1: DONE (Sprint 19 + 21)            ║${NC}"
    echo -e "${BLUE}  ║  Remaining: Phase 2-4 (Sprint 22-27)       ║${NC}"
    echo -e "${BLUE}  ║  Stop: Ctrl+C                               ║${NC}"
    echo -e "${BLUE}  ╚══════════════════════════════════════════════╝${NC}"
    echo ""
}

run_sprint() {
    local file="$1"
    local name
    name=$(basename "$file" .yaml)
    echo -e "${GREEN}  >>> Starting: $name ${NC}"
    "$SCRIPT_DIR/run.sh" "$file" --multi-agent --yes $DRY_RUN
    echo -e "${GREEN}  <<< Finished: $name ${NC}"
}

run_parallel() {
    # Run multiple sprints in parallel, wait for all to finish
    local pids=()
    for file in "$@"; do
        local name
        name=$(basename "$file" .yaml)
        echo -e "${YELLOW}  >>> Launching parallel: $name ${NC}"
        "$SCRIPT_DIR/run.sh" "$file" --multi-agent --yes $DRY_RUN &
        pids+=($!)
    done

    # Wait for all and collect exit codes
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            failed=$((failed + 1))
        fi
    done

    if [ "$failed" -gt 0 ]; then
        echo -e "${YELLOW}  WARNING: $failed sprint(s) had failures${NC}"
    fi
    return $failed
}

# Resume mode
if [ -n "$RESUME" ]; then
    echo "  Resuming from saved state..."
    "$SCRIPT_DIR/run.sh" --resume --multi-agent $DRY_RUN
    exit $?
fi

banner

# Phase 2: Sprint 22 (knowledge platform UI)
# Depends on Sprint 21 (shadcn + layout — DONE)
if [ -z "$PHASE" ] || [ "$PHASE" = "2" ]; then
    echo -e "${BLUE}  ════════════════════════════════════════${NC}"
    echo -e "${BLUE}  PHASE 2: Knowledge Platform (Sprint 22)${NC}"
    echo -e "${BLUE}  Sprint 22: Graph, Concept Hub, Smart Search, Missions${NC}"
    echo -e "${BLUE}  Mode: SEQUENTIAL (multi-agent waves inside)${NC}"
    echo -e "${BLUE}  ════════════════════════════════════════${NC}"

    run_sprint "$TASKS/sprint-22-knowledge-platform.yaml"

    echo -e "${GREEN}  PHASE 2 COMPLETE${NC}"
fi

# Phase 3: Sprint 23 (Rust gateway) + Sprint 26 (B2B admin)
# Independent — run in parallel
if [ -z "$PHASE" ] || [ "$PHASE" = "3" ]; then
    echo -e "${BLUE}  ════════════════════════════════════════${NC}"
    echo -e "${BLUE}  PHASE 3: Infra + Admin (Sprint 23 + 26)${NC}"
    echo -e "${BLUE}  Sprint 23: Rust API Gateway${NC}"
    echo -e "${BLUE}  Sprint 26: B2B Admin & Billing${NC}"
    echo -e "${BLUE}  Mode: PARALLEL${NC}"
    echo -e "${BLUE}  ════════════════════════════════════════${NC}"

    run_parallel \
        "$TASKS/sprint-23-rust-gateway.yaml" \
        "$TASKS/sprint-26-b2b-admin.yaml"

    echo -e "${GREEN}  PHASE 3 COMPLETE${NC}"
fi

# Phase 4: Sprint 24 + 25 (Rust perf) + Sprint 27 (MCP)
# Sprint 24→25 sequential (dependency), Sprint 27 parallel with them
if [ -z "$PHASE" ] || [ "$PHASE" = "4" ]; then
    echo -e "${BLUE}  ════════════════════════════════════════${NC}"
    echo -e "${BLUE}  PHASE 4: Performance + MCP (Sprint 24+25+27)${NC}"
    echo -e "${BLUE}  Sprint 24: Rust RAG Performance${NC}"
    echo -e "${BLUE}  Sprint 25: Rust IO Performance${NC}"
    echo -e "${BLUE}  Sprint 27: MCP Server & Cleanup${NC}"
    echo -e "${BLUE}  Mode: MIXED (24->25 sequential, 27 parallel)${NC}"
    echo -e "${BLUE}  ════════════════════════════════════════${NC}"

    # Run Sprint 27 in parallel with Sprint 24→25 chain
    (
        run_sprint "$TASKS/sprint-24-rust-perf.yaml"
        run_sprint "$TASKS/sprint-25-rust-infra.yaml"
    ) &
    pid_rust=$!

    run_sprint "$TASKS/sprint-27-mcp-server.yaml" &
    pid_mcp=$!

    wait "$pid_rust" || true
    wait "$pid_mcp" || true

    echo -e "${GREEN}  PHASE 4 COMPLETE${NC}"
fi

echo ""
echo -e "${GREEN}  ╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}  ║  BUILD PIPELINE COMPLETE                     ║${NC}"
echo -e "${GREEN}  ╚══════════════════════════════════════════════╝${NC}"
echo ""
