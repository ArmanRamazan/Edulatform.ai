"""
Orchestrator v2 — Agile Sprint Pipeline.

7-phase pipeline: PLANNING → DESIGN → IMPLEMENT → TEST → REVIEW → INTEGRATE → DOCUMENT.
9 role-based agents simulate a development team.

Usage:
    python main.py tasks/sprint.yaml              # run sprint
    python main.py tasks/sprint.yaml --dry-run    # preview
    python main.py --resume                       # continue
    python main.py --status                       # show progress
    python main.py --reset                        # clear state
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import signal
import sys
from pathlib import Path

# Ensure unbuffered output
if not sys.stdout.line_buffering:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]

from agent_runner import kill_all, log, request_shutdown
from config import LOG_DIR, PID_FILE, STATE_DIR, STOP_FILE
from pipeline import run_pipeline
from state import SprintFile, SprintState


# ---------------------------------------------------------------------------
# Signal handling
# ---------------------------------------------------------------------------

def _handle_signal(signum: int, _frame: object) -> None:
    name = signal.Signals(signum).name
    log(f"\n  [{name}] Shutdown requested. Finishing current tasks...")
    request_shutdown()


for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
    try:
        signal.signal(sig, _handle_signal)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# PID management
# ---------------------------------------------------------------------------

def _write_pid() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _check_pid() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return False


def _cleanup() -> None:
    kill_all()
    PID_FILE.unlink(missing_ok=True)


atexit.register(_cleanup)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_run(yaml_path: str, dry_run: bool = False) -> int:
    path = Path(yaml_path)
    if not path.exists():
        log(f"  X File not found: {path}")
        return 1

    if _check_pid():
        log("  X Another orchestrator is running. Use --reset to clear.")
        return 1

    _write_pid()
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    sprint = SprintFile.load(path)
    state = SprintState.from_sprint(sprint, str(path))

    log(f"\n  Sprint: {sprint.phase}")
    log(f"  Description: {sprint.description}")
    log(f"  Tasks: {len(sprint.tasks)}")

    if dry_run:
        log("\n  [DRY RUN] Tasks:")
        for t in sprint.tasks:
            deps = f" (depends: {t.depends_on})" if t.depends_on else ""
            log(f"    [{t.id}] {t.title} — scope: {t.scope}{deps}")
        return 0

    success = run_pipeline(state)
    return 0 if success else 1


def cmd_resume() -> int:
    state = SprintState.load()
    if not state:
        log("  X No saved state to resume. Run a sprint first.")
        return 1

    if _check_pid():
        log("  X Another orchestrator is running.")
        return 1

    _write_pid()

    state.recover_crashed()
    log(f"\n  Resuming sprint: {state.phase}")
    log(f"  Pipeline phase: {state.current_pipeline_phase}")
    log(f"  Paused at: {state.paused_at}")

    success = run_pipeline(state)
    return 0 if success else 1


def cmd_status() -> int:
    state = SprintState.load()
    if not state:
        log("  No saved state.")
        return 0

    log(f"\n  Sprint: {state.phase}")
    log(f"  Pipeline phase: {state.current_pipeline_phase}")
    log(f"  Started: {state.started_at}")
    if state.paused_at:
        log(f"  Paused: {state.paused_at}")
    log("")

    for t in state.tasks:
        icon = {"passed": "V", "failed": "X", "skipped": "-",
                "running": "~", "pending": "."}.get(t.status, "?")
        log(f"  [{icon}] {t.id}: {t.title} ({t.status})")

    passed = sum(1 for t in state.tasks if t.status == "passed")
    failed = sum(1 for t in state.tasks if t.status == "failed")
    total = len(state.tasks)
    log(f"\n  {passed}/{total} passed, {failed} failed")

    running = _check_pid()
    log(f"  Running: {'yes' if running else 'no'}")
    return 0


def cmd_reset() -> int:
    state_file = STATE_DIR / "state.json"
    if state_file.exists():
        state_file.unlink()
        log("  State cleared.")
    PID_FILE.unlink(missing_ok=True)
    STOP_FILE.unlink(missing_ok=True)
    log("  Reset complete.")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Orchestrator v2 — Agile Sprint Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("yaml_file", nargs="?", help="YAML sprint file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without executing")
    parser.add_argument("--resume", action="store_true", help="Resume from saved state")
    parser.add_argument("--status", action="store_true", help="Show sprint progress")
    parser.add_argument("--reset", action="store_true", help="Clear state and PID")

    args = parser.parse_args()

    if args.status:
        return cmd_status()
    if args.reset:
        return cmd_reset()
    if args.resume:
        return cmd_resume()
    if args.yaml_file:
        return cmd_run(args.yaml_file, dry_run=args.dry_run)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
