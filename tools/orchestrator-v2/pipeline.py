"""Orchestrator v2 — 7-phase agile pipeline."""

from __future__ import annotations

from agent_runner import is_shutdown, log
from config import MAX_RETRIES, PHASES
from executor import run_implement
from integrator import run_document, run_integrate
from planner import run_design, run_planning
from state import SprintState, _now
from verifier import run_review_phase, run_test_phase


def _print_report(state: SprintState) -> None:
    log(f"\n{'#' * 60}")
    log(f"  SPRINT REPORT: {state.phase}")
    log(f"{'#' * 60}")
    log(f"  Pipeline phase: {state.current_pipeline_phase}")
    log(f"  Started: {state.started_at}")
    log("")

    for t in state.tasks:
        icon = {
            "passed": "V",
            "failed": "X",
            "skipped": "-",
            "running": "~",
            "pending": ".",
        }.get(t.status, "?")
        retries = f" (attempts: {t.attempts})" if t.attempts > 1 else ""
        error = f" — {t.error[:80]}" if t.error else ""
        log(f"  [{icon}] {t.id}: {t.title}{retries}{error}")

    passed = sum(1 for t in state.tasks if t.status == "passed")
    failed = sum(1 for t in state.tasks if t.status == "failed")
    skipped = sum(1 for t in state.tasks if t.status == "skipped")
    total = len(state.tasks)
    log(f"\n  Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    log(f"{'#' * 60}\n")


def run_pipeline(state: SprintState) -> bool:
    """Execute the full 7-phase agile pipeline with retry on failure."""

    log(f"\n{'#' * 60}")
    log(f"  AGILE SPRINT: {state.phase}")
    log(f"  Tasks: {len(state.tasks)}")
    log(f"  Pipeline: {' → '.join(PHASES)}")
    log(f"{'#' * 60}")

    # Determine starting phase (for resume)
    start_idx = 0
    if state.current_pipeline_phase:
        try:
            start_idx = PHASES.index(state.current_pipeline_phase)
        except ValueError:
            start_idx = 0

    retry_count = 0

    for phase_idx in range(start_idx, len(PHASES)):
        if is_shutdown():
            log("\n  SHUTDOWN — saving state...")
            state.paused_at = _now()
            state.save()
            _print_report(state)
            return False

        phase = PHASES[phase_idx]

        success = _run_phase(phase, state)

        if not success:
            if phase in ("TEST", "REVIEW"):
                retry_count += 1
                if retry_count <= MAX_RETRIES:
                    log(f"\n  ! {phase} failed — retry {retry_count}/{MAX_RETRIES}")
                    log(f"  Returning to IMPLEMENT phase...")

                    # Reset task statuses for re-implementation
                    _reset_failed_tasks(state)
                    state.save()

                    # Re-run from IMPLEMENT
                    impl_ok = run_implement(state)
                    if not impl_ok:
                        log("  X Re-implementation failed")
                        _print_report(state)
                        return False

                    # Re-run current phase
                    phase_idx -= 1  # will increment in loop
                    continue
                else:
                    log(f"\n  X Max retries ({MAX_RETRIES}) exhausted on {phase}")
                    _print_report(state)
                    return False
            else:
                log(f"\n  X Phase {phase} failed — sprint aborted")
                _print_report(state)
                return False

    log(f"\n{'#' * 60}")
    log(f"  SPRINT COMPLETE: {state.phase}")
    log(f"{'#' * 60}")
    _print_report(state)
    state.current_pipeline_phase = "DONE"
    state.save()
    return True


def _run_phase(phase: str, state: SprintState) -> bool:
    if phase == "PLANNING":
        return run_planning(state)
    elif phase == "DESIGN":
        return run_design(state)
    elif phase == "IMPLEMENT":
        return run_implement(state)
    elif phase == "TEST":
        ok, _ = run_test_phase(state)
        return ok
    elif phase == "REVIEW":
        ok, _ = run_review_phase(state)
        return ok
    elif phase == "INTEGRATE":
        return run_integrate(state)
    elif phase == "DOCUMENT":
        return run_document(state)
    else:
        log(f"  X Unknown phase: {phase}")
        return False


def _reset_failed_tasks(state: SprintState) -> None:
    """Reset failed/passed tasks for re-implementation after review failure."""
    for t in state.tasks:
        if t.status in ("failed", "passed"):
            t.status = "pending"
            t.error = ""
            t.attempts = 0
