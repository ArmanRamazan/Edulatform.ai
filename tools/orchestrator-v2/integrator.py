"""Orchestrator v2 — INTEGRATE and DOCUMENT phases."""

from __future__ import annotations

import subprocess

from agent_runner import has_git_changes, log, run_agent, run_git
from config import PRODUCT_ANALYST, ROOT, TECH_LEAD
from state import SprintState


# ---------------------------------------------------------------------------
# Phase 6: INTEGRATE
# ---------------------------------------------------------------------------

def run_integrate(state: SprintState) -> bool:
    """Phase 6: INTEGRATE — ensure all changes are committed."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 6: INTEGRATE")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "INTEGRATE"
    state.save()

    if not has_git_changes():
        log("  No uncommitted changes (already committed by agents)")
        log("  V INTEGRATE complete")
        return True

    # Stage and commit any remaining changes
    run_git(["add", "-A"])
    scope = _extract_scope(state)
    msg = f"feat({scope}): {state.phase}"

    code, output = run_git(["commit", "-m", msg])
    if code != 0:
        log(f"  X Commit failed: {output[:200]}")
        return False

    log(f"  V Committed: {msg}")
    return True


def _extract_scope(state: SprintState) -> str:
    scopes = {
        t.scope.split(":")[-1] if ":" in t.scope else t.scope
        for t in state.tasks
    }
    if len(scopes) == 1:
        return scopes.pop()
    return "multi"


# ---------------------------------------------------------------------------
# Phase 7: DOCUMENT
# ---------------------------------------------------------------------------

def _build_docs_prompt(state: SprintState) -> str:
    tasks_info = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope}, status: {t.status})"
        for t in state.tasks
    )
    return (
        f"You are the tech lead updating documentation after a sprint.\n\n"
        f"## Sprint: {state.phase}\n\n"
        f"## Completed tasks:\n{tasks_info}\n\n"
        f"## Your job — update ONLY files that need changes:\n\n"
        f"Check and update as needed (ONLY if changes are relevant):\n"
        f"- README.md — if new service, test count change, or phase status change\n"
        f"- STRUCTURE.md — if new files/directories added\n"
        f"- docs/TECHNICAL-OVERVIEW.md — if new service, port, or tech change\n"
        f"- docs/architecture/01-SYSTEM-OVERVIEW.md — if system diagram changed\n"
        f"- docs/architecture/02-API-REFERENCE.md — if new endpoints added\n"
        f"- docs/architecture/03-DATABASE-SCHEMAS.md — if DB schema changed\n"
        f"- docs/architecture/04-AUTH-FLOW.md — if auth flow changed\n"
        f"- docs/architecture/05-INFRASTRUCTURE.md — if infra changed\n"
        f"- docs/architecture/06-SHARED-LIBRARY.md — if common lib changed\n"
        f"- docs/phases/PHASE-*.md — if phase task completed\n\n"
        f"Read each file first, then update ONLY what changed. Do NOT rewrite entire files.\n"
        f"Commit with: docs: update documentation for {state.phase}"
    )


def _build_impact_prompt(state: SprintState) -> str:
    tasks_info = "\n".join(
        f"  - [{t.id}] {t.title} (scope: {t.scope}, status: {t.status})"
        for t in state.tasks
    )
    passed = sum(1 for t in state.tasks if t.status == "passed")
    failed = sum(1 for t in state.tasks if t.status == "failed")
    return (
        f"You are the product analyst writing a sprint impact report.\n\n"
        f"## Sprint: {state.phase}\n"
        f"## Results: {passed} passed, {failed} failed\n\n"
        f"## Tasks:\n{tasks_info}\n\n"
        f"## Review output:\n{state.review_output[:1000]}\n\n"
        f"## Your job:\n"
        f"Write a brief impact summary (max 300 words):\n"
        f"1. What was delivered\n"
        f"2. Metrics that may be affected\n"
        f"3. Monitoring recommendations\n"
        f"4. Known risks or follow-ups\n\n"
        f"Output the report as markdown. Do NOT write code."
    )


def run_document(state: SprintState) -> bool:
    """Phase 7: DOCUMENT — tech-lead updates docs + product-analyst writes report."""
    log(f"\n{'=' * 60}")
    log(f"  PHASE 7: DOCUMENT")
    log(f"{'=' * 60}")

    state.current_pipeline_phase = "DOCUMENT"
    state.save()

    # Tech lead: update docs
    docs_prompt = _build_docs_prompt(state)
    code, output = run_agent(TECH_LEAD, docs_prompt, task_id="docs")
    if code != 0:
        log(f"  X Documentation update failed (exit={code})")
        # Non-fatal — continue to impact report

    # Commit docs if changes
    if has_git_changes():
        run_git(["add", "-A"])
        run_git(["commit", "-m", f"docs: update documentation for {state.phase}"])
        log("  V Documentation committed")

    # Product analyst: impact report (non-blocking)
    impact_prompt = _build_impact_prompt(state)
    a_code, a_output = run_agent(PRODUCT_ANALYST, impact_prompt, task_id="impact")
    if a_code == 0:
        log("  V Impact report generated")
        # Save report to logs
        from config import LOG_DIR
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        report_path = LOG_DIR / f"impact-{state.phase}.md"
        report_path.write_text(a_output)
        log(f"  Saved to {report_path}")
    else:
        log("  ! Impact report failed (non-critical)")

    log("  V DOCUMENT complete")
    return True
